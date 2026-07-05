import logging
import re
from typing import List, Dict, Any
# pyrefly: ignore [missing-import]
from neo4j import GraphDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jGraphDB:
    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.driver = None
        self.active = False
        self._mock_db = {"nodes": [], "relationships": []}
        self._connect()

    def _connect(self):
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            self.active = True
            logger.info("Connected to Neo4j database successfully.")
            self._init_constraints()
        except Exception as e:
            logger.warning(
                f"Failed to connect to Neo4j at {self.uri}: {e}. Running in Graph Mock mode."
            )
            self.active = False
            self.driver = None

    def _init_constraints(self):
        """
        Creates uniqueness constraints for graph nodes.
        """
        if not self.active:
            return
        
        # Neo4j 5+ syntax for constraints
        queries = [
            "CREATE CONSTRAINT machine_id IF NOT EXISTS FOR (m:Machine) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT engineer_id IF NOT EXISTS FOR (e:Engineer) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT failure_id IF NOT EXISTS FOR (f:Failure) REQUIRE f.id IS UNIQUE",
            "CREATE CONSTRAINT part_id IF NOT EXISTS FOR (p:SparePart) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.id IS UNIQUE",
            "CREATE CONSTRAINT maintenance_id IF NOT EXISTS FOR (m:MaintenanceRecord) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT inspection_id IF NOT EXISTS FOR (i:InspectionReport) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT sop_id IF NOT EXISTS FOR (s:SOP) REQUIRE s.id IS UNIQUE"
        ]
        
        with self.driver.session() as session:
            for query in queries:
                try:
                    session.run(query)
                except Exception as e:
                    logger.warning(f"Constraint creation skipped or failed: {e}")

    def execute_write(self, cypher: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Executes a write transaction query.
        """
        if not self.active:
            # Emulate in mock
            logger.debug(f"Mock execute_write Cypher: {cypher} | params: {parameters}")
            # Try to store nodes from common MERGE statements in mock dictionary for E2E display
            self._mock_write_emulation(cypher, parameters)
            return []

        parameters = parameters or {}
        with self.driver.session() as session:
            try:
                result = session.run(cypher, parameters)
                return [dict(record) for record in result]
            except Exception as e:
                logger.error(f"Neo4j write query failed: {cypher}. Error: {e}")
                raise e

    def execute_read(self, cypher: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Executes a read transaction query.
        """
        if not self.active:
            logger.debug(f"Mock execute_read Cypher: {cypher}")
            return self._mock_read_emulation(cypher, parameters)

        parameters = parameters or {}
        with self.driver.session() as session:
            try:
                result = session.run(cypher, parameters)
                return [dict(record) for record in result]
            except Exception as e:
                logger.error(f"Neo4j read query failed: {cypher}. Error: {e}")
                return []

    def close(self):
        if self.driver:
            self.driver.close()
            logger.info("Neo4j driver connection closed.")

    def get_all_nodes_and_edges(self) -> Dict[str, List[Any]]:
        """
        Retrieves the complete graph layout for React Flow rendering.
        """
        if not self.active:
            return self._mock_db

        cypher_nodes = "MATCH (n) RETURN id(n) as internal_id, labels(n)[0] as label, properties(n) as properties"
        cypher_edges = "MATCH (n)-[r]->(m) RETURN id(r) as edge_id, id(n) as source, id(m) as target, type(r) as label"
        
        nodes = []
        edges = []
        
        try:
            node_results = self.execute_read(cypher_nodes)
            edge_results = self.execute_read(cypher_edges)
            
            for record in node_results:
                props = record["properties"]
                # Determine node name
                name = props.get("name") or props.get("title") or props.get("id") or "Node"
                nodes.append({
                    "id": str(record["internal_id"]),
                    "type": record["label"],
                    "data": {**props, "label": f"{record['label']}: {name}"}
                })
                
            for record in edge_results:
                edges.append({
                    "id": str(record["edge_id"]),
                    "source": str(record["source"]),
                    "target": str(record["target"]),
                    "label": record["label"]
                })
                
            return {"nodes": nodes, "relationships": edges}
        except Exception as e:
            logger.error(f"Error fetching entire graph details: {e}")
            return self._mock_db

    _NODE_MERGE_RE = re.compile(r"MERGE \(n:(\w+) \{id: \$id\}\) SET n \+= \$properties")
    _REL_MERGE_RE = re.compile(r"MERGE \(s\)-\[r:(\w+)\]->\(t\)")

    def _mock_write_emulation(self, cypher: str, parameters: Dict[str, Any]):
        """
        Emulates Neo4j MERGE writes against the in-memory mock graph when no real
        Neo4j instance is connected, so entity extraction from uploaded documents
        (see app.services.entity_extractor) is still reflected in the Knowledge
        Graph view instead of being silently discarded.

        Recognizes the two write patterns used by this codebase:
          - Node upsert:  MERGE (n:Label {id: $id}) SET n += $properties
          - Relationship: MATCH (s {id: $source_id}) MATCH (t {id: $target_id})
                          MERGE (s)-[r:TYPE]->(t) SET r += $properties
        """
        parameters = parameters or {}
        cypher_norm = " ".join(cypher.split())

        node_match = self._NODE_MERGE_RE.search(cypher_norm)
        if node_match:
            label = node_match.group(1)
            node_id = parameters.get("id")
            props = parameters.get("properties", {}) or {}
            existing = next((n for n in self._mock_db["nodes"] if n["data"].get("id") == node_id), None)
            name = props.get("name") or props.get("title") or node_id
            if existing:
                existing["type"] = label
                existing["data"] = {**props, "label": f"{label}: {name}"}
            else:
                self._mock_db["nodes"].append({
                    "id": f"n{len(self._mock_db['nodes']) + 1}_{node_id}",
                    "type": label,
                    "data": {**props, "label": f"{label}: {name}"}
                })
            return

        rel_match = self._REL_MERGE_RE.search(cypher_norm)
        if rel_match and "source_id" in parameters and "target_id" in parameters:
            rel_type = rel_match.group(1)
            source_node = next((n for n in self._mock_db["nodes"] if n["data"].get("id") == parameters["source_id"]), None)
            target_node = next((n for n in self._mock_db["nodes"] if n["data"].get("id") == parameters["target_id"]), None)
            if source_node and target_node:
                already_exists = any(
                    e["source"] == source_node["id"] and e["target"] == target_node["id"] and e["label"] == rel_type
                    for e in self._mock_db["relationships"]
                )
                if not already_exists:
                    self._mock_db["relationships"].append({
                        "id": f"e{len(self._mock_db['relationships']) + 1}",
                        "source": source_node["id"],
                        "target": target_node["id"],
                        "label": rel_type
                    })
            else:
                logger.debug(
                    "Mock write emulation: could not resolve source/target node for relationship %s (source_id=%s, target_id=%s)",
                    rel_type, parameters.get("source_id"), parameters.get("target_id")
                )
            return

        logger.debug(f"Mock write emulation: unrecognized cypher pattern, skipped: {cypher_norm[:150]}")

    def _mock_read_emulation(self, cypher: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        # No specialized read patterns are emulated; the mock graph is exposed
        # directly via get_all_nodes_and_edges() instead.
        return []

    def load_centurion_mock_graph(self):
        """
        Loads the OPTIONAL Centurion Plant Train 2 sample dataset (see
        app.services.seed_data) into the graph. This is never called
        automatically — it only runs when explicitly requested, e.g. via
        `POST /api/v1/graph/reseed`, so the runtime never depends on demo data.
        """
        from app.services.seed_data import CENTURION_MOCK_NODES, CENTURION_MOCK_EDGES
        mock_nodes = CENTURION_MOCK_NODES
        mock_edges = CENTURION_MOCK_EDGES

        if not self.active:
            self._mock_db = {"nodes": mock_nodes, "relationships": mock_edges}
            logger.info("Mock database populated with enriched Centurion Plant Train 2 items (14 nodes, 21 edges).")
            return
 
        # Active Neo4j insertion
        for node in mock_nodes:
            lbl = node["type"]
            props = node["data"]
            # Convert attributes dictionary into Cypher properties format
            cypher = f"MERGE (n:{lbl} {{id: $id}}) SET n += $properties"
            self.execute_write(cypher, {"id": props["id"], "properties": props})
            
        for edge in mock_edges:
            # We must map mock IDs to node IDs in Neo4j
            source_props = next(n["data"] for n in mock_nodes if n["id"] == edge["source"])
            target_props = next(n["data"] for n in mock_nodes if n["id"] == edge["target"])
            source_lbl = next(n["type"] for n in mock_nodes if n["id"] == edge["source"])
            target_lbl = next(n["type"] for n in mock_nodes if n["id"] == edge["target"])
            
            cypher = f"""
            MATCH (s:{source_lbl} {{id: $source_id}})
            MATCH (t:{target_lbl} {{id: $target_id}})
            MERGE (s)-[r:{edge['label']}]->(t)
            """
            self.execute_write(cypher, {
                "source_id": source_props["id"],
                "target_id": target_props["id"]
            })
        logger.info("Neo4j database seeded with Centurion Plant Train 2 items.")


graph_db = Neo4jGraphDB()

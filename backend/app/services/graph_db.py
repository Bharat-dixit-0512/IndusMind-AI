import logging
from typing import List, Dict, Any, Tuple
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

    def _mock_write_emulation(self, cypher: str, parameters: Dict[str, Any]):
        """
        Adds simple nodes/edges to mock storage for visual verification if Neo4j is offline.
        """
        parameters = parameters or {}
        # Parse very simple MERGE / CREATE queries to populate the frontend mock view
        # We will pre-populate mock data for our Centurion Petrochemical Plant dataset if Neo4j is offline.
        pass

    def _mock_read_emulation(self, cypher: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Provide pre-seeded mock graph records if database is inactive
        if "MATCH (n) RETURN" in cypher or "MATCH (n)-[r]->" in cypher:
            return []
        return []

    def load_centurion_mock_graph(self):
        """
        Seeds standard nodes and edges representing the Centurion Plant Train 2.
        Includes enriched SparePart, Location, Operator, and InspectionReport relationships.
        """
        # If Neo4j is active, we insert using Cypher. If inactive, we populate the internal mock database.
        mock_nodes = [
            # Locations
            {"id": "n1",  "type": "Location",         "data": {"id": "LOC-T2",        "name": "Train 2 Processing Area",        "label": "Location: Train 2"}},
            {"id": "n11", "type": "Location",         "data": {"id": "LOC-UTIL",      "name": "Train 2 Utility Bay",            "label": "Location: Utility Bay"}},
            # Machines
            {"id": "n2",  "type": "Machine",          "data": {"id": "P-102",         "name": "Centrifugal Pump P-102",         "type": "Pump",       "status": "OPERATIONAL", "label": "Machine: Pump P-102"}},
            {"id": "n3",  "type": "Machine",          "data": {"id": "C-301",         "name": "Reciprocating Compressor C-301", "type": "Compressor", "status": "WARNING",     "label": "Machine: Compressor C-301"}},
            # Engineers
            {"id": "n4",  "type": "Engineer",         "data": {"id": "ENG-ER",        "name": "Elena Rostova",  "specialization": "Rotary Equipment",    "label": "Engineer: Elena Rostova"}},
            {"id": "n5",  "type": "Engineer",         "data": {"id": "ENG-MV",        "name": "Marcus Vance",   "specialization": "Vibration Specialist", "label": "Engineer: Marcus Vance"}},
            {"id": "n12", "type": "Engineer",         "data": {"id": "OPR-AM",        "name": "Ahmad Malik",    "specialization": "Operator - Train 2",   "label": "Operator: Ahmad Malik"}},
            # Spare Parts
            {"id": "n6",  "type": "SparePart",        "data": {"id": "PART-IMP402",   "name": "Impeller Kit K-402",    "part_number": "IMP-402",   "stock": 4, "label": "SparePart: Impeller Kit"}},
            {"id": "n13", "type": "SparePart",        "data": {"id": "PART-SEAL-S100","name": "Mechanical Seal S-100", "part_number": "SEAL-S100", "stock": 7, "label": "SparePart: Seal S-100"}},
            # Failure
            {"id": "n7",  "type": "Failure",          "data": {"id": "FAIL-P102-1",   "symptom": "High vibration and seal leakage", "root_cause": "Misaligned shaft and worn impeller bearings", "severity": "CRITICAL", "label": "Failure: Vibrations/Leak"}},
            # Maintenance Records
            {"id": "n8",  "type": "MaintenanceRecord","data": {"id": "WO-9844",        "date": "2026-05-14", "action_taken": "Shaft realigned, Impeller Kit K-402 and Seal S-100 replaced", "label": "Maintenance: WO-9844"}},
            # SOPs
            {"id": "n9",  "type": "SOP",              "data": {"id": "SOP-MECH-022",  "title": "Standard Shaft Alignment Protocol", "code": "SOP-MECH-022", "label": "SOP: Shaft Alignment"}},
            # Inspection Reports
            {"id": "n10", "type": "InspectionReport", "data": {"id": "INSP-P102-JUN2026","date": "2026-06-28", "checklist_version": "v1.2", "score": 75, "label": "Inspection: INSP-P102-JUN2026"}},
            {"id": "n14", "type": "InspectionReport", "data": {"id": "INSP-C301-JUN2026","date": "2026-06-30", "checklist_version": "v1.1", "score": 68, "label": "Inspection: INSP-C301-JUN2026"}},
        ]

        mock_edges = [
            # Spatial / location hierarchy
            {"id": "e1",  "source": "n2",  "target": "n1",  "label": "LOCATED_AT"},
            {"id": "e2",  "source": "n3",  "target": "n1",  "label": "LOCATED_AT"},
            {"id": "e15", "source": "n11", "target": "n1",  "label": "PART_OF"},
            {"id": "e16", "source": "n13", "target": "n11", "label": "STORED_IN"},
            # Maintenance work order chains
            {"id": "e3",  "source": "n8",  "target": "n2",  "label": "ON_MACHINE"},
            {"id": "e4",  "source": "n4",  "target": "n8",  "label": "PERFORMED"},
            {"id": "e5",  "source": "n8",  "target": "n6",  "label": "REPLACED_WITH"},
            {"id": "e17", "source": "n8",  "target": "n13", "label": "REPLACED_WITH"},
            {"id": "e10", "source": "n8",  "target": "n9",  "label": "FOLLOWED_SOP"},
            # Failure linkages
            {"id": "e6",  "source": "n7",  "target": "n2",  "label": "OCCURRED_ON"},
            {"id": "e7",  "source": "n8",  "target": "n7",  "label": "RESOLVED"},
            # Engineer responsibilities
            {"id": "e8",  "source": "n4",  "target": "n2",  "label": "RESPONSIBLE_FOR"},
            {"id": "e9",  "source": "n5",  "target": "n3",  "label": "RESPONSIBLE_FOR"},
            # Inspection → Machine / Failure / SOP
            {"id": "e11", "source": "n10", "target": "n2",  "label": "INSPECTED_ON"},
            {"id": "e12", "source": "n10", "target": "n7",  "label": "LOGGED_INCIDENT"},
            {"id": "e13", "source": "n10", "target": "n9",  "label": "COMPARED_TO"},
            {"id": "e18", "source": "n10", "target": "n9",  "label": "FOLLOWED_SOP"},
            {"id": "e19", "source": "n14", "target": "n3",  "label": "INSPECTED_ON"},
            # Operator conducted inspections
            {"id": "e20", "source": "n12", "target": "n10", "label": "CONDUCTED_BY"},
            {"id": "e21", "source": "n12", "target": "n14", "label": "CONDUCTED_BY"},
        ]

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
# Preseed mock graph database locally
graph_db.load_centurion_mock_graph()

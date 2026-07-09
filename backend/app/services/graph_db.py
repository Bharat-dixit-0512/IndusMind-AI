import logging
import re
from typing import List, Dict, Any, Iterable
# pyrefly: ignore [missing-import]
from neo4j import GraphDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

# See app.services.entity_extractor for why this exists: Neo4j labels/
# relationship types must be string-interpolated into Cypher (the driver
# can't parameterize them), so anything interpolated here is validated first.
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(value: Any, default: str) -> str:
    if isinstance(value, str) and _SAFE_IDENTIFIER_RE.match(value) and len(value) <= 64:
        return value
    logger.warning(f"Rejected unsafe graph label/relationship type: {value!r}; using {default!r} instead.")
    return default


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
            "CREATE CONSTRAINT sop_id IF NOT EXISTS FOR (s:SOP) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
        ]

        with self.driver.session() as session:
            for query in queries:
                try:
                    session.run(query)
                except Exception as e:
                    logger.warning(f"Constraint creation skipped or failed: {e}")

    def execute_write(self, cypher: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Executes a write transaction query against the real Neo4j driver. Only
        ever called while `self.active` is True — every mock-mode code path
        has its own explicit in-memory implementation (see upsert_node,
        upsert_relationship, remove_document_entities, etc.) instead of
        emulating arbitrary Cypher, since pattern-matching raw query strings
        is fragile and was a real source of bugs (mock mode silently dropping
        writes it didn't recognize).
        """
        if not self.active:
            logger.debug(f"execute_write called while in mock mode; no-op. Cypher: {cypher}")
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
        Executes a read transaction query against the real Neo4j driver. See
        execute_write for why mock mode just no-ops here instead of emulating
        arbitrary Cypher.
        """
        if not self.active:
            logger.debug(f"execute_read called while in mock mode; returning empty. Cypher: {cypher}")
            return []

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

    # ── Document/entity lifecycle ────────────────────────────────────────
    #
    # Every entity node and relationship carries a `document_ids` array of
    # every currently-uploaded document that created or references it. An
    # entity mentioned in several of one user's documents is exactly ONE
    # node/edge referenced by several document IDs — never one duplicate per
    # document. Deleting a document (remove_document_entities) removes its ID
    # from that array everywhere and only deletes the node/relationship
    # outright once the array is empty, so entities/relationships still used
    # by surviving documents are never touched.

    def upsert_document(self, document_id: str, filename: str, user_id: str,
                        file_type: str = None, upload_time: str = None) -> str:
        """
        Creates/updates the Document node representing one uploaded file, the
        single source of truth every extracted entity hangs off of. Returns
        its graph node id. Carries the document's own metadata (id, filename,
        user, type, upload time) so the graph is self-describing.
        """
        doc_node_id = f"DOCUMENT::{document_id}"
        properties = {"id": doc_node_id, "document_id": document_id, "filename": filename, "user_id": user_id}
        if file_type is not None:
            properties["file_type"] = file_type
        if upload_time is not None:
            properties["upload_time"] = upload_time

        if self.active:
            self.execute_write(
                "MERGE (d:Document {id: $id}) SET d += $properties",
                {"id": doc_node_id, "properties": properties}
            )
            return doc_node_id

        existing = next((n for n in self._mock_db["nodes"] if n["data"].get("id") == doc_node_id), None)
        if existing:
            existing["data"] = {**properties, "label": f"Document: {filename}"}
        else:
            self._mock_db["nodes"].append({
                "id": f"n{len(self._mock_db['nodes']) + 1}_{doc_node_id}",
                "type": "Document",
                "data": {**properties, "label": f"Document: {filename}"},
            })
        return doc_node_id

    def link_mention(self, document_node_id: str, entity_id: str) -> None:
        """
        Records that `document_node_id` mentions `entity_id` (a
        Document -[:MENTIONS]-> Entity provenance edge). This edge is never
        shared/merged across documents — it always originates from exactly
        one Document node — so it needs no document_ids bookkeeping of its
        own: DETACH DELETE-ing that Document node (see
        remove_document_entities) cleanly removes it.
        """
        if self.active:
            self.execute_write(
                "MATCH (d:Document {id: $doc_id}) MATCH (n {id: $entity_id}) MERGE (d)-[:MENTIONS]->(n)",
                {"doc_id": document_node_id, "entity_id": entity_id}
            )
            return

        doc_node = next((n for n in self._mock_db["nodes"] if n["data"].get("id") == document_node_id), None)
        entity_node = next((n for n in self._mock_db["nodes"] if n["data"].get("id") == entity_id), None)
        if not doc_node or not entity_node:
            return
        exists = any(
            e["source"] == doc_node["id"] and e["target"] == entity_node["id"] and e["label"] == "MENTIONS"
            for e in self._mock_db["relationships"]
        )
        if not exists:
            self._mock_db["relationships"].append({
                "id": f"e{len(self._mock_db['relationships']) + 1}",
                "source": doc_node["id"],
                "target": entity_node["id"],
                "label": "MENTIONS",
            })

    def upsert_node(self, label: str, node_id: str, properties: Dict[str, Any], document_id: str) -> None:
        """
        Creates or updates an entity node, merging `document_id` into its
        `document_ids` array instead of overwriting it — so the same entity
        mentioned across multiple documents becomes ONE node referenced by
        several documents, rather than a duplicate node per document.
        """
        safe_label = _safe_identifier(label, "Entity")

        if self.active:
            cypher = f"""
            MERGE (n:{safe_label} {{id: $id}})
            SET n += $properties
            SET n.document_ids = CASE
                WHEN n.document_ids IS NULL THEN [$document_id]
                WHEN NOT $document_id IN n.document_ids THEN n.document_ids + $document_id
                ELSE n.document_ids
            END
            """
            self.execute_write(cypher, {"id": node_id, "properties": properties, "document_id": document_id})
            return

        existing = next((n for n in self._mock_db["nodes"] if n["data"].get("id") == node_id), None)
        name = properties.get("name") or properties.get("title") or node_id
        if existing:
            doc_ids = list(existing["data"].get("document_ids") or [])
            if document_id not in doc_ids:
                doc_ids.append(document_id)
            existing["type"] = safe_label
            existing["data"] = {**properties, "document_ids": doc_ids, "label": f"{safe_label}: {name}"}
        else:
            self._mock_db["nodes"].append({
                "id": f"n{len(self._mock_db['nodes']) + 1}_{node_id}",
                "type": safe_label,
                "data": {**properties, "document_ids": [document_id], "label": f"{safe_label}: {name}"},
            })

    def upsert_relationship(
        self, source_id: str, target_id: str, rel_type: str, properties: Dict[str, Any], document_id: str
    ) -> None:
        """
        Creates or updates a relationship between two already-scoped entity
        nodes, merging `document_id` into its `document_ids` array — the same
        relationship independently asserted by multiple documents (e.g. two
        resumes both saying "Jane WORKED_AT Acme") accumulates document IDs
        instead of being treated as unrelated duplicate edges.
        """
        safe_rel = _safe_identifier(rel_type, "RELATED_TO")

        if self.active:
            cypher = f"""
            MATCH (s {{id: $source_id}})
            MATCH (t {{id: $target_id}})
            MERGE (s)-[r:{safe_rel}]->(t)
            SET r += $properties
            SET r.document_ids = CASE
                WHEN r.document_ids IS NULL THEN [$document_id]
                WHEN NOT $document_id IN r.document_ids THEN r.document_ids + $document_id
                ELSE r.document_ids
            END
            """
            self.execute_write(cypher, {
                "source_id": source_id, "target_id": target_id,
                "properties": properties, "document_id": document_id,
            })
            return

        source_node = next((n for n in self._mock_db["nodes"] if n["data"].get("id") == source_id), None)
        target_node = next((n for n in self._mock_db["nodes"] if n["data"].get("id") == target_id), None)
        if not source_node or not target_node:
            logger.debug(
                "Mock upsert_relationship: could not resolve source/target node (source_id=%s, target_id=%s)",
                source_id, target_id,
            )
            return

        existing = next(
            (e for e in self._mock_db["relationships"]
             if e["source"] == source_node["id"] and e["target"] == target_node["id"] and e["label"] == safe_rel),
            None,
        )
        if existing:
            doc_ids = list(existing.get("document_ids") or [])
            if document_id not in doc_ids:
                doc_ids.append(document_id)
            existing["document_ids"] = doc_ids
        else:
            self._mock_db["relationships"].append({
                "id": f"e{len(self._mock_db['relationships']) + 1}",
                "source": source_node["id"],
                "target": target_node["id"],
                "label": safe_rel,
                "document_ids": [document_id],
            })

    def remove_document_entities(self, document_id: str) -> None:
        """
        Called when a document is deleted. Removes the Document node itself
        (and its MENTIONS edges), then strips `document_id` out of every
        entity node's and relationship's `document_ids` array — deleting the
        node/relationship outright only once no uploaded document references
        it anymore. Entities/relationships still used by other surviving
        documents are always preserved.
        """
        if self.active:
            try:
                self.execute_write(
                    "MATCH (d:Document {document_id: $document_id}) DETACH DELETE d",
                    {"document_id": document_id}
                )
                self.execute_write(
                    """
                    MATCH (n) WHERE $document_id IN coalesce(n.document_ids, [])
                    SET n.document_ids = [x IN n.document_ids WHERE x <> $document_id]
                    WITH n WHERE size(n.document_ids) = 0
                    DETACH DELETE n
                    """,
                    {"document_id": document_id}
                )
                self.execute_write(
                    """
                    MATCH ()-[r]->() WHERE $document_id IN coalesce(r.document_ids, [])
                    SET r.document_ids = [x IN r.document_ids WHERE x <> $document_id]
                    WITH r WHERE size(r.document_ids) = 0
                    DELETE r
                    """,
                    {"document_id": document_id}
                )
                logger.info(
                    f"Removed document {document_id} from the knowledge graph "
                    "(references cleared; fully-orphaned nodes/relationships deleted)."
                )
            except Exception as e:
                logger.error(f"Could not remove graph entities for document {document_id}: {e}")
            return

        # Mock mode: mirror the same three steps in Python.
        before = len(self._mock_db["nodes"])
        doc_node_id = f"DOCUMENT::{document_id}"
        doc_rf_node = next((n for n in self._mock_db["nodes"] if n["data"].get("id") == doc_node_id), None)

        if doc_rf_node:
            self._mock_db["nodes"] = [n for n in self._mock_db["nodes"] if n["id"] != doc_rf_node["id"]]
            self._mock_db["relationships"] = [
                e for e in self._mock_db["relationships"]
                if e["source"] != doc_rf_node["id"] and e["target"] != doc_rf_node["id"]
            ]

        orphaned_ids = set()
        for n in self._mock_db["nodes"]:
            doc_ids = n["data"].get("document_ids")
            if doc_ids and document_id in doc_ids:
                remaining = [d for d in doc_ids if d != document_id]
                n["data"]["document_ids"] = remaining
                if not remaining:
                    orphaned_ids.add(n["id"])
        if orphaned_ids:
            self._mock_db["nodes"] = [n for n in self._mock_db["nodes"] if n["id"] not in orphaned_ids]
            self._mock_db["relationships"] = [
                e for e in self._mock_db["relationships"]
                if e["source"] not in orphaned_ids and e["target"] not in orphaned_ids
            ]

        kept_relationships = []
        for e in self._mock_db["relationships"]:
            doc_ids = e.get("document_ids")
            if doc_ids and document_id in doc_ids:
                remaining = [d for d in doc_ids if d != document_id]
                if not remaining:
                    continue
                e["document_ids"] = remaining
            kept_relationships.append(e)
        self._mock_db["relationships"] = kept_relationships

        removed = before - len(self._mock_db["nodes"])
        if removed:
            logger.info(f"Removed {removed} orphaned mock graph node(s) after deleting document {document_id}.")

    def reconcile_with_documents(self, valid_document_ids: Iterable[str]) -> None:
        """
        Self-healing pass run at startup (mirrors
        VectorStoreService.reconcile_with_documents): strips any document ID
        that no longer exists in PostgreSQL out of every node's/
        relationship's `document_ids`, deleting anything left fully
        orphaned, and removes Document nodes for documents that no longer
        exist. This catches deletions that happened before this
        document-lifecycle model existed, or while Neo4j was unreachable, so
        the graph always represents only currently-uploaded documents.
        """
        valid_ids = list(valid_document_ids)
        valid_id_set = set(valid_ids)

        if self.active:
            try:
                self.execute_write(
                    "MATCH (d:Document) WHERE NOT d.document_id IN $valid_ids DETACH DELETE d",
                    {"valid_ids": valid_ids}
                )
                # Normalize any legacy single-document_id nodes/relationships
                # (from before this array-based model existed) onto the new
                # schema so they get reconciled below instead of ignored.
                self.execute_write(
                    "MATCH (n) WHERE n.document_id IS NOT NULL AND n.document_ids IS NULL "
                    "SET n.document_ids = [n.document_id]"
                )
                self.execute_write(
                    "MATCH ()-[r]->() WHERE r.document_id IS NOT NULL AND r.document_ids IS NULL "
                    "SET r.document_ids = [r.document_id]"
                )
                self.execute_write(
                    """
                    MATCH (n) WHERE n.document_ids IS NOT NULL
                    SET n.document_ids = [x IN n.document_ids WHERE x IN $valid_ids]
                    WITH n WHERE size(n.document_ids) = 0
                    DETACH DELETE n
                    """,
                    {"valid_ids": valid_ids}
                )
                self.execute_write(
                    """
                    MATCH ()-[r]->() WHERE r.document_ids IS NOT NULL
                    SET r.document_ids = [x IN r.document_ids WHERE x IN $valid_ids]
                    WITH r WHERE size(r.document_ids) = 0
                    DELETE r
                    """,
                    {"valid_ids": valid_ids}
                )
                # Final sweep: delete any remaining entity node that has NO
                # document provenance at all (document_ids null or empty and
                # not a legacy singular document_id). This is what removes
                # ownerless demo/seed nodes and any pre-lifecycle orphans, so
                # the graph strictly reflects only currently-uploaded
                # documents. Document nodes are excluded (handled above by the
                # valid-ids check).
                self.execute_write(
                    """
                    MATCH (n)
                    WHERE NOT n:Document
                      AND size(coalesce(n.document_ids, [])) = 0
                      AND n.document_id IS NULL
                    DETACH DELETE n
                    """
                )
                logger.info(f"Graph database reconciled against {len(valid_ids)} existing document(s).")
            except Exception as e:
                logger.error(f"Failed to reconcile graph database with documents: {e}")
            return

        # Mock mode: mirror the same logic in Python.
        stale_doc_rf_ids = {
            n["id"] for n in self._mock_db["nodes"]
            if n["type"] == "Document" and n["data"].get("document_id") not in valid_id_set
        }
        if stale_doc_rf_ids:
            self._mock_db["nodes"] = [n for n in self._mock_db["nodes"] if n["id"] not in stale_doc_rf_ids]
            self._mock_db["relationships"] = [
                e for e in self._mock_db["relationships"]
                if e["source"] not in stale_doc_rf_ids and e["target"] not in stale_doc_rf_ids
            ]

        orphaned_ids = set()
        for n in self._mock_db["nodes"]:
            if n["type"] == "Document":
                continue  # Document nodes handled above by the valid-ids check
            data = n["data"]
            doc_ids = data.get("document_ids")
            if doc_ids is None and data.get("document_id") is not None:
                doc_ids = [data["document_id"]]  # legacy single-document node
            if doc_ids is None:
                # No document provenance at all (ownerless demo/seed or
                # pre-lifecycle orphan) — purge, so the graph reflects only
                # currently-uploaded documents.
                orphaned_ids.add(n["id"])
                continue
            remaining = [d for d in doc_ids if d in valid_id_set]
            data["document_ids"] = remaining
            if not remaining:
                orphaned_ids.add(n["id"])
        if orphaned_ids:
            self._mock_db["nodes"] = [n for n in self._mock_db["nodes"] if n["id"] not in orphaned_ids]
            self._mock_db["relationships"] = [
                e for e in self._mock_db["relationships"]
                if e["source"] not in orphaned_ids and e["target"] not in orphaned_ids
            ]

        kept_relationships = []
        for e in self._mock_db["relationships"]:
            doc_ids = e.get("document_ids")
            if doc_ids is not None:
                remaining = [d for d in doc_ids if d in valid_id_set]
                if not remaining:
                    continue
                e["document_ids"] = remaining
            kept_relationships.append(e)
        self._mock_db["relationships"] = kept_relationships

    def find_recurring_entities(self, user_id: str, min_documents: int = 2, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Finds entities that recur across two or more of this user's
        documents — e.g. the same machine appearing in both a work order and
        an inspection report, or the same skill across two resumes. Reads
        each node's own `document_ids` array directly (populated by
        upsert_node), rather than re-deriving it by walking MENTIONS edges,
        since every merged entity node already knows exactly which documents
        reference it.
        """
        if self.active:
            cypher = """
            MATCH (n)
            WHERE n.user_id = $user_id AND n.name IS NOT NULL
              AND size(coalesce(n.document_ids, [])) >= $min_documents
            OPTIONAL MATCH (d:Document) WHERE d.document_id IN n.document_ids
            WITH n, collect(DISTINCT d.filename) AS documents
            RETURN labels(n)[0] AS type, n.name AS name, documents, size(n.document_ids) AS doc_count
            ORDER BY doc_count DESC
            LIMIT $limit
            """
            return self.execute_read(cypher, {"user_id": user_id, "min_documents": min_documents, "limit": limit})

        # Mock equivalent: read document_ids straight off each entity node.
        doc_filename_by_id = {
            n["data"].get("document_id"): n["data"].get("filename")
            for n in self._mock_db["nodes"] if n["type"] == "Document"
        }
        results = []
        for n in self._mock_db["nodes"]:
            data = n.get("data", {})
            if data.get("user_id") != user_id or not data.get("name"):
                continue
            doc_ids = data.get("document_ids") or []
            if len(doc_ids) < min_documents:
                continue
            documents = sorted({doc_filename_by_id.get(d, d) for d in doc_ids})
            results.append({"type": n.get("type"), "name": data["name"], "documents": documents, "doc_count": len(doc_ids)})

        results.sort(key=lambda r: r["doc_count"], reverse=True)
        return results[:limit]

    def get_owned_graph(self, user_id: str) -> Dict[str, List[Any]]:
        """
        Returns the subgraph owned by `user_id` — the shared ownership filter
        used by the /graph endpoint, the planner agent, and the Maintenance/
        Compliance/Reports dashboards, so they all read the exact same
        knowledge graph. Only nodes whose `user_id` matches are returned:
        ownerless nodes (which could only come from the removed demo-seed
        feature or pre-lifecycle orphans) are never shown, so the graph
        reflects strictly this user's uploaded documents. Never exposes
        another user's entities.
        """
        graph_data = self.get_all_nodes_and_edges()
        owned_nodes = [
            n for n in graph_data.get("nodes", [])
            if n.get("data", {}).get("user_id") == user_id
        ]
        owned_ids = {n["id"] for n in owned_nodes}
        owned_edges = [
            e for e in graph_data.get("relationships", [])
            if e["source"] in owned_ids and e["target"] in owned_ids
        ]
        return {"nodes": owned_nodes, "relationships": owned_edges}

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


graph_db = Neo4jGraphDB()

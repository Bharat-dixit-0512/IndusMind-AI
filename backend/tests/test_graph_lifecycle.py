"""
Tests for knowledge-graph document lifecycle management (see
app.services.graph_db.upsert_node / upsert_relationship /
remove_document_entities): the same entity mentioned across a user's
documents must merge into one node tagged with every referencing document's
ID, and deleting a document must only remove entities/relationships no
surviving document still references.
"""
import io
import uuid

from conftest import register_user, auth_headers


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _skill_nodes(client, headers, name: str):
    resp = client.get("/api/v1/graph/", headers=headers)
    assert resp.status_code == 200
    return [
        n for n in resp.json()["nodes"]
        if n["type"] == "Skill" and (n["data"].get("name") or "").lower() == name.lower()
    ]


def test_shared_entity_merges_and_survives_partial_deletion(client):
    token = register_user(client, unique_email("graphmerge"))
    headers = auth_headers(token)

    r1 = client.post(
        "/api/v1/documents/upload", headers=headers,
        files={"file": ("resume1.txt", io.BytesIO(b"I have strong experience in Python and Docker."), "text/plain")},
    )
    assert r1.status_code == 201, r1.text
    doc1_id = r1.json()["id"]

    r2 = client.post(
        "/api/v1/documents/upload", headers=headers,
        files={"file": ("resume2.txt", io.BytesIO(b"My second project also used Python extensively."), "text/plain")},
    )
    assert r2.status_code == 201, r2.text
    doc2_id = r2.json()["id"]

    # Python is mentioned in both documents -> must merge into ONE node
    # tagged with both document IDs, not two duplicate nodes.
    python_nodes = _skill_nodes(client, headers, "python")
    assert len(python_nodes) == 1, "the same entity mentioned in two documents must merge into one node"
    assert set(python_nodes[0]["data"]["document_ids"]) == {doc1_id, doc2_id}

    # Docker is only mentioned in the first document.
    docker_nodes = _skill_nodes(client, headers, "docker")
    assert len(docker_nodes) == 1
    assert docker_nodes[0]["data"]["document_ids"] == [doc1_id]

    # Delete doc1 (mentions both Python and Docker). Python must survive
    # (doc2 still references it) with doc1's ID removed from its
    # document_ids; Docker must be fully removed since no surviving document
    # references it anymore.
    resp = client.delete(f"/api/v1/documents/delete/{doc1_id}", headers=headers)
    assert resp.status_code == 200

    python_nodes = _skill_nodes(client, headers, "python")
    assert len(python_nodes) == 1, "shared entity must not be deleted while another document still references it"
    assert python_nodes[0]["data"]["document_ids"] == [doc2_id]

    docker_nodes = _skill_nodes(client, headers, "docker")
    assert docker_nodes == [], "entity referenced only by the deleted document must be fully removed"

    # Delete doc2 too -> Python must now be fully gone as well.
    resp = client.delete(f"/api/v1/documents/delete/{doc2_id}", headers=headers)
    assert resp.status_code == 200

    python_nodes = _skill_nodes(client, headers, "python")
    assert python_nodes == [], "entity referenced by no surviving document must be fully removed"


def test_machine_id_variants_merge_to_one_node(client):
    """
    'Pump P-102', 'P102' and 'Pump-P102' refer to the same asset and must
    normalize to a single Machine node (see entity_extractor._canonical_machine),
    not three near-duplicates.
    """
    token = register_user(client, unique_email("dedup"))
    headers = auth_headers(token)

    resp = client.post(
        "/api/v1/documents/upload", headers=headers,
        files={"file": ("wo.txt", io.BytesIO(
            b"Work order for Pump P-102. The P102 pump was inspected. Pump-P102 seal replaced."
        ), "text/plain")},
    )
    assert resp.status_code == 201, resp.text

    graph = client.get("/api/v1/graph/", headers=headers).json()
    machines = [n for n in graph["nodes"] if n["type"] == "Machine"]
    codes = {n["data"].get("code") for n in machines}
    assert codes == {"P-102"}, f"machine variants must merge to one node, got {codes}"
    assert len(machines) == 1

    # The Document node must carry its own metadata (source of truth).
    doc_nodes = [n for n in graph["nodes"] if n["type"] == "Document"]
    assert len(doc_nodes) == 1
    assert doc_nodes[0]["data"].get("file_type") == "txt"
    assert doc_nodes[0]["data"].get("filename") == "wo.txt"


def test_delete_removes_document_node_itself(client):
    token = register_user(client, unique_email("graphdocnode"))
    headers = auth_headers(token)

    resp = client.post(
        "/api/v1/documents/upload", headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"Uses Kubernetes for orchestration."), "text/plain")},
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]

    graph = client.get("/api/v1/graph/", headers=headers).json()
    assert any(n["type"] == "Document" and n["data"].get("document_id") == doc_id for n in graph["nodes"])

    client.delete(f"/api/v1/documents/delete/{doc_id}", headers=headers)

    graph = client.get("/api/v1/graph/", headers=headers).json()
    assert not any(n["type"] == "Document" and n["data"].get("document_id") == doc_id for n in graph["nodes"])
    assert not any(n["type"] == "Skill" and (n["data"].get("name") or "").lower() == "kubernetes" for n in graph["nodes"])


def test_ownerless_and_orphan_nodes_are_purged_and_never_shown(client):
    """
    An ownerless node (no user_id, no document provenance) — the shape the old
    demo-seed feature produced — must never appear in any user's graph and must
    be purged by reconcile, so the graph reflects only uploaded documents.
    """
    from app.services.graph_db import graph_db

    # Simulate leftover demo/seed pollution directly in the graph store.
    graph_db._mock_db["nodes"].append({
        "id": "seed_1", "type": "Machine",
        "data": {"id": "SEED-PUMP", "name": "Centrifugal Pump P-102", "label": "Machine: Centrifugal Pump P-102"},
    })
    graph_db._mock_db["nodes"].append({
        "id": "seed_2", "type": "Engineer",
        "data": {"id": "SEED-ENG", "name": "Elena Rostova", "label": "Engineer: Elena Rostova"},
    })
    graph_db._mock_db["relationships"].append({
        "id": "seed_rel", "source": "seed_1", "target": "seed_2", "label": "MAINTAINED_BY",
    })

    token = register_user(client, unique_email("seedcheck"))
    headers = auth_headers(token)

    # Ownerless seed nodes must never be visible to a user.
    graph = client.get("/api/v1/graph/", headers=headers).json()
    assert not any((n["data"].get("name") or "") in ("Centrifugal Pump P-102", "Elena Rostova") for n in graph["nodes"])

    # Maintenance overview must not count seed nodes as discovered assets.
    overview = client.get("/api/v1/maintenance/overview", headers=headers).json()
    assert not any(a["name"] in ("Centrifugal Pump P-102", "Elena Rostova") for a in overview["assets"])

    # Reconcile against the real (empty) document set must physically purge them.
    graph_db.reconcile_with_documents(set())
    remaining = {n["id"] for n in graph_db._mock_db["nodes"]}
    assert "seed_1" not in remaining and "seed_2" not in remaining
    assert not any(r["id"] == "seed_rel" for r in graph_db._mock_db["relationships"])

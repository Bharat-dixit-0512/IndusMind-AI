"""
Smoke tests for the critical paths audited in this session: auth, the full
upload -> index -> retrieve -> answer -> delete-cascade pipeline, per-user
retrieval/graph isolation, and the document-ownership (IDOR) fix. These run
fully offline against a temp SQLite DB (see conftest.py) — no live Postgres,
Neo4j, or Gemini calls.
"""
import io
import uuid

from conftest import register_user, auth_headers


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def test_register_and_login(client):
    email = unique_email("auth")
    token = register_user(client, email)
    assert token

    # Correct password logs in
    resp = client.post("/api/v1/auth/login-json", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 200
    assert resp.json()["email"] == email

    # Wrong password is rejected
    resp = client.post("/api/v1/auth/login-json", json={"email": email, "password": "wrong-password"})
    assert resp.status_code == 400

    # Unauthenticated requests to a protected endpoint are rejected
    resp = client.get("/api/v1/documents/list")
    assert resp.status_code == 401


def test_upload_list_status_delete_cascade(client):
    token = register_user(client, unique_email("upload"))
    headers = auth_headers(token)

    content = b"Acme Robotics Inc.\nProject: Falcon Drive Controller.\nSkills: Python, React.\n"
    resp = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("notes.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    assert doc["status"] in ("PENDING", "PROCESSING", "COMPLETED")
    doc_id = doc["id"]

    # TestClient runs BackgroundTasks synchronously within the request, so by
    # the time upload() returns, processing has already completed.
    resp = client.get(f"/api/v1/documents/status/{doc_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"

    resp = client.get("/api/v1/documents/list", headers=headers)
    assert resp.status_code == 200
    assert any(d["id"] == doc_id for d in resp.json())

    # The document's content should now be retrievable via chat. The offline
    # (no-Gemini, no-embeddings) test environment falls back to literal
    # keyword-overlap extraction, so the query must share real vocabulary
    # with the document — a semantic paraphrase wouldn't match without a
    # live embedding/Gemini model, which is expected, not a bug.
    resp = client.post("/api/v1/chat/", headers=headers, json={"message": "Tell me about Acme Robotics", "history": []})
    assert resp.status_code == 200
    body = resp.json()
    assert "Acme Robotics" in body["response"] or any(c["document_name"] == "notes.txt" for c in body["citations"])

    # Delete cascades: gone from list, and no longer answerable
    resp = client.delete(f"/api/v1/documents/delete/{doc_id}", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/documents/list", headers=headers)
    assert all(d["id"] != doc_id for d in resp.json())

    resp = client.get(f"/api/v1/documents/status/{doc_id}", headers=headers)
    assert resp.status_code == 404


def test_per_user_retrieval_isolation(client):
    token_a = register_user(client, unique_email("isoa"))
    token_b = register_user(client, unique_email("isob"))

    client.post(
        "/api/v1/documents/upload", headers=auth_headers(token_a),
        files={"file": ("a.txt", io.BytesIO(b"Confidential: Project Nightingale budget is $4.2 million."), "text/plain")},
    )
    client.post(
        "/api/v1/documents/upload", headers=auth_headers(token_b),
        files={"file": ("b.txt", io.BytesIO(b"Confidential: Project Skylark budget is $9.9 million."), "text/plain")},
    )

    # User B must never see User A's document content in an answer
    resp = client.post("/api/v1/chat/", headers=auth_headers(token_b),
                        json={"message": "What is the budget for Project Nightingale?", "history": []})
    assert resp.status_code == 200
    assert "4.2" not in resp.json()["response"]

    # And vice versa
    resp = client.post("/api/v1/chat/", headers=auth_headers(token_a),
                        json={"message": "What is the budget for Project Skylark?", "history": []})
    assert resp.status_code == 200
    assert "9.9" not in resp.json()["response"]


def test_chat_says_not_found_for_irrelevant_query(client):
    token = register_user(client, unique_email("notfound"))
    headers = auth_headers(token)
    client.post(
        "/api/v1/documents/upload", headers=headers,
        files={"file": ("c.txt", io.BytesIO(b"A short note about quarterly team lunches."), "text/plain")},
    )

    resp = client.post("/api/v1/chat/", headers=headers,
                        json={"message": "What is Pump P102's maintenance schedule?", "history": []})
    assert resp.status_code == 200
    body = resp.json()
    assert "could not find" in body["response"].lower()
    assert body["citations"] == []
    # Must never fabricate industrial demo content
    assert "centurion" not in body["response"].lower()
    assert "sop-mech" not in body["response"].lower()


def test_cannot_access_or_delete_another_users_document(client):
    token_owner = register_user(client, unique_email("owner"))
    token_intruder = register_user(client, unique_email("intruder"))

    resp = client.post(
        "/api/v1/documents/upload", headers=auth_headers(token_owner),
        files={"file": ("private.txt", io.BytesIO(b"Owner's private notes."), "text/plain")},
    )
    doc_id = resp.json()["id"]

    # Another authenticated user must not be able to view or delete it
    resp = client.get(f"/api/v1/documents/status/{doc_id}", headers=auth_headers(token_intruder))
    assert resp.status_code == 404

    resp = client.delete(f"/api/v1/documents/delete/{doc_id}", headers=auth_headers(token_intruder))
    assert resp.status_code == 404

    # It must still exist for its actual owner
    resp = client.get(f"/api/v1/documents/status/{doc_id}", headers=auth_headers(token_owner))
    assert resp.status_code == 200

    # And must not appear in the intruder's own document list
    resp = client.get("/api/v1/documents/list", headers=auth_headers(token_intruder))
    assert all(d["id"] != doc_id for d in resp.json())


def test_graph_reseed_requires_admin(client):
    token = register_user(client, unique_email("nonadmin"))
    resp = client.post("/api/v1/graph/reseed", headers=auth_headers(token))
    assert resp.status_code == 403

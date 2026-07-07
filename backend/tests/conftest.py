"""
Test isolation setup. This module runs at collection time, BEFORE any test
module imports app.main (or anything that transitively imports it) — so the
environment variables set here take effect before the singletons in
app.services.vector_store / app.services.graph_db / app.core.config are ever
constructed.

Critically, this means the smoke test suite NEVER touches:
  - the real Postgres database configured in backend/.env
  - the real Neo4j instance
  - the real Gemini API (no network calls, no quota usage)
  - the real FAISS/fallback vector index files under backend/vector_store/

Everything runs against a fresh temp SQLite database, a deliberately
unreachable Neo4j URI (so graph_db falls back to its in-memory mock — fast
failure, not a slow timeout), and no Gemini key (so retrieval/answers use the
pure keyword + extractive-summary fallback path deterministically).
"""
import os
import tempfile

_TEST_DIR = tempfile.mkdtemp(prefix="et_hack_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TEST_DIR, 'test.db')}"
os.environ["NEO4J_URI"] = "bolt://127.0.0.1:1"  # unreachable -> fails fast, forces mock mode
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "test"
os.environ["GEMINI_API_KEY"] = ""  # forces offline/extractive-only mode, no live API calls
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["UPLOAD_DIR"] = os.path.join(_TEST_DIR, "uploads")
os.environ["REPORT_DIR"] = os.path.join(_TEST_DIR, "reports")
os.environ["FAISS_INDEX_PATH"] = os.path.join(_TEST_DIR, "vector_store")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def register_user(client: TestClient, email: str, password: str = "testpass123", full_name: str = "Test User") -> str:
    """Registers a fresh user and returns their bearer token."""
    resp = client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": full_name
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

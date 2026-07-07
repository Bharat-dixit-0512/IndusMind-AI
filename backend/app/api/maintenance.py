"""
Maintenance Intelligence API. Everything here is derived from the EXISTING
knowledge base — the Neo4j graph (entities extracted at ingestion), the
Postgres document catalog (with auto-detected categories), and FAISS chunks
(via the maintenance agent) — never a separate pipeline and never demo data.
"""
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.services.graph_db import graph_db
from app.services.vector_store import vector_store
from app.services.document_classifier import MAINTENANCE_CATEGORIES
from app.agents.maintenance_agent import maintenance_agent
from app.api.deps import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Graph node types that represent maintenance-relevant physical/organizational
# assets discovered from uploaded documents.
_ASSET_TYPES = ["Machine", "Equipment", "SparePart", "Engineer", "Location",
                "Failure", "MaintenanceRecord", "InspectionReport", "WorkOrder", "SOP"]

# Categories whose documents represent incidents/failures worth surfacing first.
_INCIDENT_CATEGORIES = {"Incident Report", "Inspection Report"}


def _owned_documents(db: Session, current_user: User) -> List[Document]:
    query = db.query(Document)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Document.uploaded_by == current_user.id)
    return query.order_by(Document.created_at.desc()).all()


def _doc_out(doc: Document) -> Dict[str, Any]:
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "category": doc.category,
        "status": doc.status.value if isinstance(doc.status, DocumentStatus) else doc.status,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.get("/overview")
def maintenance_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Auto-populates the Maintenance dashboard from the shared knowledge base:
    discovered assets (from the graph), maintenance-relevant documents (from
    the Postgres catalog + auto-classification), recent incidents, and
    recurring cross-document patterns. Returns has_data=False with an
    explanatory message when the user has uploaded no maintenance documents,
    rather than an empty page.
    """
    user_id = str(current_user.id)

    # 1. Discovered assets from the SAME Neo4j graph the graph view uses.
    graph = graph_db.get_owned_graph(user_id)
    assets = []
    asset_counts: Dict[str, int] = {}
    for node in graph.get("nodes", []):
        if node.get("type") not in _ASSET_TYPES:
            continue
        data = node.get("data", {})
        name = data.get("name") or data.get("title") or data.get("id")
        if not name:
            continue
        doc_ids = data.get("document_ids") or []
        assets.append({
            "id": node["id"],
            "type": node["type"],
            "name": name,
            "doc_count": len(doc_ids) if isinstance(doc_ids, list) else 0,
        })
        asset_counts[node["type"]] = asset_counts.get(node["type"], 0) + 1

    # Most-referenced assets first, so the dashboard leads with what matters.
    assets.sort(key=lambda a: a["doc_count"], reverse=True)

    # 2. Maintenance-relevant documents from the Postgres catalog.
    all_docs = _owned_documents(db, current_user)
    maintenance_docs = [d for d in all_docs if (d.category or "") in MAINTENANCE_CATEGORIES]
    recent_incidents = [
        _doc_out(d) for d in maintenance_docs if (d.category or "") in _INCIDENT_CATEGORIES
    ][:10]

    # 3. Recurring entities across two or more documents (lessons-learned /
    #    "similar failures" signal), restricted to maintenance asset types.
    patterns = [
        p for p in graph_db.find_recurring_entities(user_id)
        if p.get("type") in _ASSET_TYPES
    ]

    has_data = bool(assets or maintenance_docs)
    if not has_data:
        completed = any(d.status == DocumentStatus.COMPLETED for d in all_docs)
        if not all_docs:
            message = ("No documents uploaded yet. Upload maintenance logs, machine manuals, "
                       "inspection or incident reports to automatically populate this dashboard.")
        elif not completed:
            message = "Your documents are still being processed. Maintenance intelligence will appear once processing completes."
        else:
            message = ("No maintenance-related documents detected among your uploads. Upload "
                       "maintenance logs, machine manuals, inspection or incident reports to populate this dashboard.")
    else:
        message = f"Discovered {len(assets)} asset(s) across {len(maintenance_docs)} maintenance document(s)."

    return {
        "has_data": has_data,
        "message": message,
        "assets": assets,
        "asset_counts": asset_counts,
        "documents": [_doc_out(d) for d in maintenance_docs],
        "recent_incidents": recent_incidents,
        "recurring_patterns": patterns,
    }


@router.get("/asset/{asset_name}")
def maintenance_asset_detail(
    asset_name: str,
    current_user: User = Depends(get_current_user),
):
    """
    Root Cause Analysis + maintenance history for a specific discovered
    asset, generated on demand from that asset's retrieved document chunks —
    so the user can click an asset instead of typing a query. Grounded only
    in uploaded documents (see maintenance_agent).
    """
    chunks = vector_store.search(asset_name, k=8, user_id=str(current_user.id))
    report = maintenance_agent.generate_rca(asset_name, chunks)
    citations = []
    seen = set()
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        fname = meta.get("filename", "Unknown Document")
        if fname in seen:
            continue
        seen.add(fname)
        citations.append({"document_name": fname, "page_number": meta.get("chunk_index"),
                          "text": (chunk.get("page_content") or "")[:200]})
    return {"asset": asset_name, "report": report, "citations": citations if report.get("confidence_score", 0) > 0 else []}

"""
Reports API. Every report is generated from the EXISTING knowledge base:
retrieved FAISS chunks + Neo4j graph relationships, grounded via the same
maintenance/compliance/knowledge agents used everywhere else. Each report
embeds citations, an AI confidence score and a generated timestamp, and
exports to PDF. No mock reports, no demo content.
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.report import Report, ReportType
from app.models.user import User, UserRole
from app.schemas.report import ReportCreate, ReportOut
from app.services.report_generator import generate_pdf_report
from app.services.vector_store import vector_store
from app.services.graph_db import graph_db
from app.agents.compliance_agent import compliance_agent
from app.agents.maintenance_agent import maintenance_agent
from app.agents.knowledge_agent import knowledge_agent
from app.api.deps import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def _gather_context(query: str, user_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """
    Pulls the shared knowledge base for a report: retrieved chunks (FAISS),
    per-source citations, and graph relationship triples (Neo4j) relevant to
    the query. Reused across every report type.
    """
    chunks = vector_store.search(query, k=8, user_id=user_id)

    citations: List[Dict[str, Any]] = []
    seen = set()
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        fname = meta.get("filename", "Unknown Document")
        if fname in seen:
            continue
        seen.add(fname)
        citations.append({
            "document_name": fname,
            "page_number": meta.get("chunk_index"),
            "text": (chunk.get("page_content") or "")[:200],
        })

    # Graph relationships from the SAME Neo4j graph, matched to the query's
    # named entities where possible, otherwise a representative sample.
    graph = graph_db.get_owned_graph(user_id)
    nodes_by_id = {n["id"]: n for n in graph.get("nodes", [])}
    query_lower = query.lower()

    def node_label(n):
        d = n.get("data", {})
        return f"{n.get('type')}: {d.get('name') or d.get('title') or d.get('id')}"

    matched, other = [], []
    for e in graph.get("relationships", []):
        if e.get("label") == "MENTIONS":
            continue  # provenance edges aren't meaningful in a narrative report
        s, t = nodes_by_id.get(e["source"]), nodes_by_id.get(e["target"])
        if not s or not t:
            continue
        triple = f"{node_label(s)} —{e['label']}→ {node_label(t)}"
        s_name = str(s.get("data", {}).get("name", "")).lower()
        t_name = str(t.get("data", {}).get("name", "")).lower()
        if (s_name and s_name in query_lower) or (t_name and t_name in query_lower):
            matched.append(triple)
        else:
            other.append(triple)
    graph_triples = (matched or other)[:12]

    return chunks, citations, graph_triples


def _owned_report_or_404(db: Session, report_id: uuid.UUID, current_user: User) -> Report:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or (current_user.role != UserRole.ADMIN and report.generated_by != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report record not found.")
    return report


@router.post("/generate", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def generate_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers intelligence agents to gather data from the shared knowledge base
    and generate a professional PDF report with citations, confidence and a
    generated timestamp.
    """
    unique_id = uuid.uuid4()
    report_type = payload.report_type
    pdf_filename = f"{unique_id}_{report_type.value.lower()}_report.pdf"

    user_id = str(current_user.id)
    query = payload.title
    chunks, citations, graph_triples = _gather_context(query, user_id)

    # Route to the right agent, all grounded in the retrieved chunks.
    if report_type == ReportType.COMPLIANCE:
        report_data = compliance_agent.evaluate_compliance(query, chunks)
    elif report_type in (ReportType.RCA, ReportType.MAINTENANCE):
        report_data = maintenance_agent.generate_rca(query, chunks)
    else:
        # INSPECTION / EXECUTIVE — narrative synthesis grounded in chunks.
        report_data = knowledge_agent.retrieve_sop_or_manual(query, chunks)

    # Shared provenance/metadata embedded into every report.
    report_data = {
        **report_data,
        "citations": citations,
        "graph_relationships": graph_triples,
        "confidence_score": report_data.get("confidence_score", 0.0),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "generated_by": current_user.full_name,
        "source_count": len(citations),
    }

    try:
        pdf_path = generate_pdf_report(
            filename=pdf_filename,
            title=payload.title,
            report_type=report_type.value,
            data=report_data
        )
    except Exception as pdf_err:
        logger.error(f"Failed to generate PDF document: {pdf_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile PDF: {pdf_err}"
        )

    db_report = Report(
        id=unique_id,
        title=payload.title,
        report_type=report_type.value,
        file_path=pdf_path,
        generated_by=current_user.id
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)

    return db_report


@router.get("/list", response_model=List[ReportOut])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists generated reports. Regular users see only their own; ADMIN sees all.
    """
    query = db.query(Report)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Report.generated_by == current_user.id)
    return query.order_by(Report.created_at.desc()).all()


@router.get("/download/{report_id}")
def download_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Downloads the compiled PDF report from the file system. Only the report's
    owner (or an ADMIN) may download it.
    """
    report = _owned_report_or_404(db, report_id, current_user)

    if not os.path.exists(report.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on disk."
        )

    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename=os.path.basename(report.file_path)
    )

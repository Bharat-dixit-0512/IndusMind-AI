"""
Compliance Intelligence API. Compliance status is INFERRED from the user's
uploaded documents only — SOPs, inspection reports, audit reports, safety
procedures and regulatory documents detected by auto-classification, assessed
against each other by the compliance agent over retrieved chunks. No hardcoded
pass/fail rules, no predefined SOPs, no demo data.
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.agents.compliance_agent import compliance_agent
from app.services.vector_store import vector_store
from app.services.document_classifier import COMPLIANCE_CATEGORIES
from app.api.deps import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def _risk_level(score: int) -> str:
    if score >= 85:
        return "Low"
    if score >= 60:
        return "Medium"
    if score >= 40:
        return "High"
    return "Critical"


def _owned_documents(db: Session, current_user: User) -> List[Document]:
    query = db.query(Document)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Document.uploaded_by == current_user.id)
    return query.order_by(Document.created_at.desc()).all()


@router.post("/check")
def run_compliance_check(
    query: str,
    current_user: User = Depends(get_current_user)
):
    """
    Triggers an immediate compliance check against SOPs for a specific query/asset.
    """
    # Retrieve relevant vector chunks, scoped to this user's own documents
    chunks = vector_store.search(query, k=8, user_id=str(current_user.id))
    report = compliance_agent.evaluate_compliance(query, chunks)
    return report


@router.get("/overview")
def compliance_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Auto-populates the Compliance dashboard: detects compliance-related
    documents from the shared Postgres catalog, runs an aggregate assessment
    over retrieved chunks (compliance agent, grounded only in uploaded
    content), and derives score, passed/failed checks, deviations, risk level
    and missing document types. Explains why when the user has uploaded no
    compliance-related documents.
    """
    user_id = str(current_user.id)
    all_docs = _owned_documents(db, current_user)
    compliance_docs = [d for d in all_docs if (d.category or "") in COMPLIANCE_CATEGORIES]

    generated_at = datetime.now(timezone.utc).isoformat()
    category_counts: Dict[str, int] = {}
    for d in compliance_docs:
        category_counts[d.category] = category_counts.get(d.category, 0) + 1

    # Missing document types: which compliance document classes are absent.
    # Inferred purely from what the user has vs. hasn't uploaded — e.g. if
    # inspections exist but no SOPs, adherence can't be fully verified.
    present_categories = set(category_counts.keys())
    missing_documents = sorted(COMPLIANCE_CATEGORIES - present_categories)

    if not compliance_docs:
        completed = any(d.status == DocumentStatus.COMPLETED for d in all_docs)
        if not all_docs:
            message = ("No documents uploaded yet. Upload SOPs, inspection reports, audit reports, "
                       "safety procedures or regulatory documents to generate a compliance assessment.")
        elif not completed:
            message = "Your documents are still being processed. Compliance assessment will appear once processing completes."
        else:
            message = ("No compliance-related documents detected among your uploads. Upload SOPs, "
                       "inspection reports, audit reports, safety procedures or regulatory documents "
                       "so compliance can be assessed.")
        return {
            "has_data": False,
            "message": message,
            "compliance_score": 0,
            "risk_level": "Unknown",
            "summary": message,
            "passed_checks": 0,
            "failed_checks": 0,
            "checklist": [],
            "corrective_actions": [],
            "deviations": [],
            "detected_documents": [],
            "category_counts": {},
            "missing_documents": sorted(COMPLIANCE_CATEGORIES),
            "citations": [],
            "confidence_score": 0.0,
            "generated_at": generated_at,
        }

    # Aggregate assessment: retrieve compliance-focused chunks from the SAME
    # FAISS index and let the compliance agent evaluate them. The query steers
    # retrieval toward SOP/inspection/audit/safety content; the agent stays
    # grounded strictly in whatever chunks come back.
    assessment_query = ("Assess compliance: verify inspection results and work against SOP limits, "
                        "safety procedures, audit findings and regulatory requirements. "
                        "Identify deviations and non-conformances.")
    chunks = vector_store.search(assessment_query, k=10, user_id=user_id)
    report = compliance_agent.evaluate_compliance(assessment_query, chunks)

    checklist = report.get("checklist", []) or []
    passed = sum(1 for c in checklist if c.get("status") == "COMPLIANT")
    failed = sum(1 for c in checklist if c.get("status") == "NON_COMPLIANT")
    deviations = [c for c in checklist if c.get("status") == "NON_COMPLIANT"]
    score = int(report.get("compliance_score", 0) or 0)

    citations: List[Dict[str, Any]] = []
    if report.get("confidence_score", 0) > 0:
        seen = set()
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            fname = meta.get("filename", "Unknown Document")
            if fname in seen:
                continue
            seen.add(fname)
            citations.append({"document_name": fname, "page_number": meta.get("chunk_index"),
                              "text": (chunk.get("page_content") or "")[:200]})

    return {
        "has_data": True,
        "message": f"Assessed {len(compliance_docs)} compliance document(s).",
        "compliance_score": score,
        "risk_level": _risk_level(score),
        "summary": report.get("summary", ""),
        "passed_checks": passed,
        "failed_checks": failed,
        "checklist": checklist,
        "corrective_actions": report.get("corrective_actions", []) or [],
        "deviations": deviations,
        "detected_documents": [
            {"id": str(d.id), "filename": d.filename, "category": d.category}
            for d in compliance_docs
        ],
        "category_counts": category_counts,
        "missing_documents": missing_documents,
        "citations": citations,
        "confidence_score": report.get("confidence_score", 0.0),
        "generated_at": generated_at,
    }

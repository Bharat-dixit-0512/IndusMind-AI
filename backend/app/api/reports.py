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
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.report import Report
from app.models.user import User, UserRole
from app.schemas.report import ReportCreate, ReportOut
from app.services.report_service import create_report
from app.api.deps import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


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
    generated timestamp. Same generation path the AI chat uses (see
    app.services.report_service.create_report).
    """
    try:
        db_report, _ = create_report(db, current_user, payload.title, payload.report_type)
    except Exception as err:
        logger.error(f"Failed to generate report: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile report: {err}"
        )
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

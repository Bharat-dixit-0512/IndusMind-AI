import os
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.report import Report, ReportType
from app.schemas.report import ReportCreate, ReportOut
from app.services.report_generator import generate_pdf_report
from app.services.vector_store import vector_store
from app.agents.compliance_agent import compliance_agent
from app.agents.maintenance_agent import maintenance_agent
from app.api.deps import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def generate_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers intelligence agents to gather data and generate a professional PDF report.
    """
    unique_id = uuid.uuid4()
    pdf_filename = f"{unique_id}_{payload.report_type.value.lower()}_report.pdf"
    
    # 1. Gather context and query sub-agents
    query = f"Centurion Plant {payload.title}"
    chunks = vector_store.search(query, k=5)
    
    report_data = {}
    if payload.report_type == ReportType.COMPLIANCE:
        report_data = compliance_agent.evaluate_compliance(query, chunks)
    elif payload.report_type == ReportType.RCA:
        report_data = maintenance_agent.generate_rca(query, chunks)
    else:
        # Standard inspection log outline
        report_data = {
            "title": payload.title,
            "status": "Inspected",
            "inspector": current_user.full_name,
            "details": "General structural review completed according to safety protocols."
        }

    # 2. Build PDF using ReportLab
    try:
        pdf_path = generate_pdf_report(
            filename=pdf_filename,
            title=payload.title,
            report_type=payload.report_type.value,
            data=report_data
        )
    except Exception as pdf_err:
        logger.error(f"Failed to generate PDF document: {pdf_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile PDF: {pdf_err}"
        )
        
    # 3. Save report record to Postgres
    db_report = Report(
        id=unique_id,
        title=payload.title,
        report_type=payload.report_type,
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
    Lists all generated analytical reports.
    """
    return db.query(Report).order_by(Report.created_at.desc()).all()


@router.get("/download/{report_id}")
def download_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Downloads the compiled PDF report from the file system.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report record not found."
        )
        
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

import logging
import os
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.report import Report
from app.services.report_generator import report_generator
from app.core.config import settings

logger = logging.getLogger(__name__)


class ReportAgent:
    def __init__(self):
        pass

    def compile_pdf_report(
        self, 
        db: Session, 
        title: str, 
        report_type: str, 
        user_id: str,
        data: Dict[str, Any]
    ) -> Report:
        """
        Agent responsible for compiling engineering and compliance PDF reports.
        Receives structured payload data and generates a styled ReportLab PDF.
        """
        logger.info(f"ReportAgent compiling {report_type} report: {title}")
        
        # 1. Determine local file name
        report_id_str = os.urandom(8).hex()
        filename = f"report_{report_type.lower()}_{report_id_str}.pdf"
        file_path = os.path.join(settings.REPORT_DIR, filename)
        
        # 2. Invoke ReportLab compiler service
        try:
            report_generator.generate_pdf(
                output_path=file_path,
                title=title,
                report_type=report_type,
                data=data
            )
            logger.info(f"Report PDF compiled successfully at: {file_path}")
        except Exception as e:
            logger.error(f"ReportLab PDF compiler failed: {e}")
            # Ensure file exists or write a minimal placeholder so downloads don't crash
            with open(file_path, "w") as f:
                f.write("%PDF-1.4 ... Error compiling PDF report.")
        
        # 3. Register in PostgreSQL / relational db
        db_report = Report(
            title=title,
            report_type=report_type,
            file_path=file_path,
            generated_by=user_id
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        
        return db_report


report_agent = ReportAgent()

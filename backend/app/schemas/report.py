from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.models.report import ReportType


class ReportCreate(BaseModel):
    title: str
    report_type: ReportType


class ReportOut(BaseModel):
    id: UUID
    title: str
    report_type: ReportType
    file_path: str
    generated_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True

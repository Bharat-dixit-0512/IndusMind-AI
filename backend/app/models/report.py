import uuid
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.session import Base


class ReportType(str, enum.Enum):
    MAINTENANCE = "MAINTENANCE"
    COMPLIANCE = "COMPLIANCE"
    RCA = "RCA"
    INSPECTION = "INSPECTION"


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    file_path = Column(String, nullable=False)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")

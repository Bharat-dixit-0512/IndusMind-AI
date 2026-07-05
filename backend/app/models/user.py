import uuid
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import enum

from app.db.session import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    ENGINEER = "ENGINEER"
    INSPECTOR = "INSPECTOR"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.ENGINEER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

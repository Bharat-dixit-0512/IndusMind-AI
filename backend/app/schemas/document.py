from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.document import DocumentStatus


class DocumentBase(BaseModel):
    filename: str
    file_type: str
    file_size: int


class DocumentOut(DocumentBase):
    id: UUID
    status: DocumentStatus
    error_message: Optional[str] = None
    uploaded_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentChunkOut(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str

    class Config:
        from_attributes = True

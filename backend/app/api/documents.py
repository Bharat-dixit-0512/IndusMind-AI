import os
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentOut
from app.services.document_processing import process_document_task
from app.api.deps import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a document (PDF, DOCX, XLSX, Image) and triggers asynchronous
    background processing (parsing, embedding, indexing, graph update).
    """
    # 1. Validate file extension
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    allowed_extensions = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".txt", ".csv"]
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension {ext} not supported. Allowed formats: {', '.join(allowed_extensions)}"
        )
        
    # 2. Save file to disk
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    file_size = 0
    try:
        with open(file_path, "wb") as buffer:
            # Read in chunks of 1MB to avoid memory overflow
            while content := await file.read(1024 * 1024):
                file_size += len(content)
                buffer.write(content)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file to server: {e}"
        )
        
    # 3. Create database entry
    db_doc = Document(
        filename=filename,
        file_type=ext.replace(".", ""),
        file_path=file_path,
        file_size=file_size,
        status=DocumentStatus.PENDING,
        uploaded_by=current_user.id
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # 4. Queue background task
    background_tasks.add_task(process_document_task, str(db_doc.id))
    logger.info(f"Queued background processing for file: {filename} (id: {db_doc.id})")
    
    return db_doc


@router.get("/list", response_model=List[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists upload histories and processing statuses.
    """
    return db.query(Document).order_by(Document.created_at.desc()).all()


@router.get("/status/{document_id}", response_model=DocumentOut)
def get_document_status(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches details and processing status of a specific document.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
    return doc


@router.delete("/delete/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a document from the system, removes its file from disk,
    and cascadingly removes database chunks.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
        
    # Remove file from disk
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.error(f"Failed to delete file from disk: {e}")
            
    db.delete(doc)
    db.commit()
    return {"detail": "Document successfully deleted"}

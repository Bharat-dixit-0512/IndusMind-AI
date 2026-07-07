import logging
import os
import traceback
import uuid

from app.db.session import SessionLocal
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.ocr_service import extract_text
from app.services.chunking import split_text_into_chunks
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


def process_document_task(document_id: str, session_id: str) -> None:
    """
    Synchronous processing function intended to be run in a background executor.
    Opens its own DB session since the request-scoped session is closed by the
    time FastAPI's BackgroundTasks actually execute this function.
    1. Extracts text from file.
    2. Splits text into chunks.
    3. Saves chunks to database.
    4. Generates embeddings and saves to FAISS.
    5. Extracts entities and relationships, updates Neo4j.
    6. Updates status in PostgreSQL database.
    """
    logger.info(f"Starting background processing for document: {document_id}")
    db = SessionLocal()
    doc_uuid = uuid.UUID(document_id)

    document = db.query(Document).filter(Document.id == doc_uuid).first()
    if not document:
        logger.error(f"Document {document_id} not found in database.")
        db.close()
        return

    # Update status to PROCESSING
    document.status = DocumentStatus.PROCESSING
    db.commit()

    try:
        # Step 1: Text extraction (PyMuPDF / Tesseract fallback)
        if not os.path.exists(document.file_path):
            raise FileNotFoundError(f"File not found on disk: {document.file_path}")
            
        logger.info(f"Extracting text from: {document.file_path}")
        text_content = extract_text(document.file_path)
        
        if not text_content.strip():
            raise ValueError("No text could be extracted from this document.")
            
        logger.info(f"Text extraction complete. Characters extracted: {len(text_content)}")

        # Step 1.5: Auto-classify the document type from its own text, so the
        # Maintenance / Compliance / Reports dashboards can be populated
        # automatically. Non-blocking: a classification failure must never
        # fail the whole upload.
        try:
            from app.services.document_classifier import classify_document
            document.category = classify_document(text_content, document.filename)
            db.commit()
            logger.info(f"Document classified as: {document.category}")
        except Exception as classify_err:
            logger.error(f"Document classification failed (non-blocking): {classify_err}")

        # Step 2: Chunking
        logger.info("Splitting text into chunks...")
        chunks = split_text_into_chunks(text_content)
        logger.info(f"Document split into {len(chunks)} chunks.")

        # Step 3: Save chunks to PostgreSQL & prep vectors
        texts_to_embed = []
        metadatas_to_embed = []
        
        for idx, chunk_text in enumerate(chunks):
            chunk_db = DocumentChunk(
                document_id=document.id,
                chunk_index=idx,
                content=chunk_text
            )
            db.add(chunk_db)
            
            # Prepare data for Vector database
            texts_to_embed.append(chunk_text)
            metadatas_to_embed.append({
                "document_id": str(document.id),
                "user_id": str(document.uploaded_by),
                "filename": document.filename,
                "chunk_index": idx,
                "upload_time": document.created_at.isoformat() if document.created_at else None,
                "session_id": session_id,
            })
            
        # Commit to Postgres to generate chunk IDs
        db.commit()

        # Step 4: Add chunks to FAISS Index
        logger.info("Adding chunks to FAISS index...")
        vector_store.add_chunks(texts_to_embed, metadatas_to_embed)
        logger.info("FAISS indexing complete.")

        # Step 5: Entity and Relationship extraction for Neo4j
        logger.info("Extracting entities and relationships for Neo4j...")
        try:
            from app.services.entity_extractor import extract_and_sync_entities
            extract_and_sync_entities(document.filename, text_content, str(document.uploaded_by), str(document.id))
            logger.info("Neo4j knowledge graph updated successfully.")
        except Exception as graph_err:
            logger.error(f"Neo4j extraction/sync failed (non-blocking for document status): {graph_err}")
            logger.error(traceback.format_exc())

        # Step 6: Mark document as COMPLETED
        document.status = DocumentStatus.COMPLETED
        db.commit()
        logger.info(f"Successfully processed document: {document.filename} (ID: {document_id})")

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        logger.error(traceback.format_exc())
        
        # Rollback database changes, then set status to FAILED
        db.rollback()
        
        # Re-fetch document inside transaction to avoid detached state
        document = db.query(Document).filter(Document.id == doc_uuid).first()
        if document:
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)[:500]  # Cap length
            db.commit()

    finally:
        db.close()

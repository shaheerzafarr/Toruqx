import uuid
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy import select
# pyrefly: ignore [missing-import]
import structlog

from app.core.database import get_db
from app.models.pydantic_models import TextIngestionRequest, IngestedDocumentResponse
from app.models.sqlalchemy_models import IngestedDocument, User
from app.api.v1.auth import get_current_user
from app.services.ingestion import ingestion_service
from app.services.qdrant import qdrant_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/ingestion", tags=["Document Ingestion"])

@router.post("/text", response_model=IngestedDocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_text(
    payload: TextIngestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest arbitrary raw text content, split into chunks, generate local embeddings, and save to Qdrant.
    """
    try:
        content_bytes_len = len(payload.content.encode("utf-8"))
        doc = await ingestion_service.ingest_document(
            db=db,
            filename=payload.filename,
            content=payload.content,
            file_size=content_bytes_len
        )
        if doc.status == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document ingestion failed: {doc.error_message}"
            )
        return doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ingest text route failure", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal database or vector error: {str(e)}"
        )

@router.post("/file", response_model=IngestedDocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a text file (.txt, .md, .json) to chunk, embed, and index in Qdrant.
    """
    if not file.filename.endswith((".txt", ".md", ".json")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload text-based files (.txt, .md, .json)."
        )
    
    try:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8")
        file_size = len(content_bytes)
        
        doc = await ingestion_service.ingest_document(
            db=db,
            filename=file.filename,
            content=content,
            file_size=file_size
        )
        if doc.status == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File ingestion failed: {doc.error_message}"
            )
        return doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ingest file route failure", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal database or parsing error: {str(e)}"
        )

@router.get("/status/{document_id}", response_model=IngestedDocumentResponse)
async def get_ingestion_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve database synchronization status of a specific document ingestion process.
    """
    try:
        query = select(IngestedDocument).where(IngestedDocument.id == document_id)
        result = await db.execute(query)
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document record not found."
            )
        return doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get status route failure", doc_id=str(document_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("", response_model=list[IngestedDocumentResponse])
async def list_ingested_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all ingested documents in the database, ordered by creation date descending.
    """
    try:
        query = select(IngestedDocument).order_by(IngestedDocument.created_at.desc())
        result = await db.execute(query)
        docs = result.scalars().all()
        return docs
    except Exception as e:
        logger.error("List ingested documents route failure", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ingested documents."
        )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ingested_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific ingested document, remove its chunks from Qdrant, and delete its database audit log.
    """
    try:
        # Fetch document record
        query = select(IngestedDocument).where(IngestedDocument.id == document_id)
        result = await db.execute(query)
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document record not found."
            )
            
        # Delete from Qdrant first
        await qdrant_service.delete_document("kb_documents", str(document_id))
        
        # Delete from Postgres
        await db.delete(doc)
        await db.commit()
        
        logger.info("Deleted document and associated Qdrant vectors", document_id=str(document_id), filename=doc.filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete document route failure", doc_id=str(document_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )



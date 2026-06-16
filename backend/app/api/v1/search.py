from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from app.models.pydantic_models import QueryRequest, SearchResultResponse
from app.services.embedding import embedding_service
from app.services.qdrant import qdrant_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/search", tags=["Vector Search"])

@router.post("", response_model=list[SearchResultResponse], status_code=status.HTTP_200_OK)
async def search_knowledge_base(payload: QueryRequest):
    """
    Perform semantic vector search in Qdrant with optional document metadata filtering.
    """
    try:
        # 1. Generate query embedding vector using local sentence-transformers
        query_vector = await embedding_service.get_embedding(payload.query)

        # 2. Perform similarity search in Qdrant
        doc_id_str = str(payload.document_id) if payload.document_id else None
        results = await qdrant_service.search_similarity(
            collection_name="kb_documents",
            query_vector=query_vector,
            limit=payload.limit,
            document_id=doc_id_str
        )
        return results
    except Exception as e:
        logger.error("Knowledge base search route failure", query=payload.query, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(e)}"
        )

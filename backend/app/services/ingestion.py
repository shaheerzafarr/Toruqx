import uuid
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client.http import models as qmodels

from app.models.sqlalchemy_models import IngestedDocument
from app.services.embedding import embedding_service
from app.services.qdrant import qdrant_service

logger = structlog.get_logger(__name__)

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """
    Splits text recursively by paragraphs, lines, and words to respect chunk boundaries.
    Overlap is capped so combined chunk never exceeds chunk_size.
    """
    if not text:
        return []
    
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    def _get_overlap_prefix(chunk_content: str) -> str:
        """Get overlap text, capped at half of chunk_size to prevent oversized chunks."""
        max_overlap = min(chunk_overlap, chunk_size // 2)
        overlap_idx = max(0, len(chunk_content) - max_overlap)
        return chunk_content[overlap_idx:]
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # If a single paragraph is larger than chunk_size, split it down further
        if len(para) > chunk_size:
            # Output current accumulated chunk first
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            lines = para.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if len(line) > chunk_size:
                    # Split line by words
                    words = line.split(" ")
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 > chunk_size:
                            chunks.append(temp_chunk.strip())
                            overlap_prefix = _get_overlap_prefix(temp_chunk)
                            temp_chunk = overlap_prefix + " " + word
                        else:
                            temp_chunk += " " + word
                    if temp_chunk.strip():
                        current_chunk = temp_chunk.strip()
                else:
                    if len(current_chunk) + len(line) + 1 > chunk_size:
                        chunks.append(current_chunk)
                        overlap_prefix = _get_overlap_prefix(current_chunk)
                        current_chunk = (overlap_prefix + "\n" + line).strip()
                        # Cap: if overlap pushed us over, truncate overlap
                        if len(current_chunk) > chunk_size:
                            current_chunk = line
                    else:
                        current_chunk = (current_chunk + "\n" + line).strip()
        else:
            if len(current_chunk) + len(para) + 2 > chunk_size:
                chunks.append(current_chunk)
                overlap_prefix = _get_overlap_prefix(current_chunk)
                current_chunk = (overlap_prefix + "\n\n" + para).strip()
                # Cap: if overlap pushed us over, truncate overlap
                if len(current_chunk) > chunk_size:
                    current_chunk = para
            else:
                current_chunk = (current_chunk + "\n\n" + para).strip()
                
    if current_chunk:
        chunks.append(current_chunk)
        
    return [c.strip() for c in chunks if c.strip()]


class IngestionService:

    @staticmethod
    async def process_file_ingestion_bg(
        doc_id: uuid.UUID,
        filename: str,
        content_bytes: bytes,
        user_id: uuid.UUID | None = None
    ) -> None:
        """
        Asynchronous background task to parse PDF or decode text, chunk, embed, and index it in Qdrant.
        Creates a dedicated connection session to prevent cross-request transactional pollution.
        """
        from app.core.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            try:
                # 1. Fetch document record
                query = select(IngestedDocument).where(IngestedDocument.id == doc_id)
                res = await db.execute(query)
                doc_record = res.scalar_one_or_none()
                if not doc_record:
                    logger.error("Document record not found for background task", doc_id=str(doc_id))
                    return

                # Update status to processing
                doc_record.status = "processing"
                await db.commit()
                await db.refresh(doc_record)

                # 2. Extract content based on file type
                if filename.lower().endswith(".pdf"):
                    import io
                    from pypdf import PdfReader
                    pdf_file = io.BytesIO(content_bytes)
                    reader = PdfReader(pdf_file)
                    text_parts = []
                    for page in reader.pages:
                        text_parts.append(page.extract_text() or "")
                    content = "\n".join(text_parts)
                else:
                    content = content_bytes.decode("utf-8")

                if not content.strip():
                    raise ValueError("Document content was empty or could not be parsed.")

                # 3. Chunk text (size=1000, overlap=300 for dense embeddings)
                chunks = chunk_text(content, chunk_size=1000, chunk_overlap=300)
                doc_record.chunk_count = len(chunks)
                await db.commit()

                if not chunks:
                    raise ValueError("Document content could not be split into valid chunks.")

                # 4. Generate local embeddings
                logger.info("Generating embeddings for background chunks...", count=len(chunks), filename=filename)
                embeddings = await embedding_service.get_embeddings(chunks)

                # 5. Prepare Qdrant points
                points = []
                for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                    point_id = str(uuid.uuid4())
                    points.append(
                        qmodels.PointStruct(
                            id=point_id,
                            vector=vector,
                            payload={
                                "document_id": str(doc_id),
                                "user_id": str(user_id) if user_id else None,
                                "filename": filename,
                                "text": chunk,
                                "chunk_index": idx
                            }
                        )
                    )

                # 6. Upload points to Qdrant
                logger.info("Uploading background points to Qdrant...", points_count=len(points))
                await qdrant_service.client.upsert(
                    collection_name="kb_documents",
                    wait=True,
                    points=points
                )

                # 7. Update status to completed
                doc_record.status = "completed"
                await db.commit()

                # Invalidate cache
                try:
                    from app.services.redis_cache import redis_service
                    await redis_service.clear_cache_pattern("rag_cache:*")
                except Exception as cache_err:
                    logger.error("Failed to clear RAG cache on background ingestion", error=str(cache_err))

                logger.info("Background document ingestion completed successfully.", filename=filename, doc_id=str(doc_id))

            except Exception as e:
                logger.exception("Background document ingestion pipeline failure", doc_id=str(doc_id), error=str(e))
                # H-2: Rollback potentially broken session state before updating error status
                try:
                    await db.rollback()
                    query = select(IngestedDocument).where(IngestedDocument.id == doc_id)
                    res = await db.execute(query)
                    doc_record = res.scalar_one_or_none()
                    if doc_record:
                        doc_record.status = "failed"
                        doc_record.error_message = str(e)
                        await db.commit()
                except Exception as db_err:
                    logger.error("Failed to set failed status in database", error=str(db_err))

ingestion_service = IngestionService()

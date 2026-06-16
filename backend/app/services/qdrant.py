# pyrefly: ignore [missing-import]
from qdrant_client import AsyncQdrantClient
# pyrefly: ignore [missing-import]
from qdrant_client.http import models as qmodels
# pyrefly: ignore [missing-import]
from qdrant_client.http.exceptions import UnexpectedResponse
# pyrefly: ignore [missing-import]
import structlog
# pyrefly: ignore [missing-import]
from app.core.config import settings

logger = structlog.get_logger(__name__)

class QdrantService:
    def __init__(self):
        self.client: AsyncQdrantClient | None = None

    async def connect(self) -> None:
        if not self.client:
            logger.info("Initializing connection to Qdrant...", url=settings.QDRANT_URL)
            self.client = AsyncQdrantClient(url=settings.QDRANT_URL)
            # Fetch collections list to verify connectivity
            await self.client.get_collections()
            logger.info("Successfully connected to Qdrant.")

    async def disconnect(self) -> None:
        if self.client:
            logger.info("Closing Qdrant connections...")
            await self.client.close()
            self.client = None
            logger.info("Qdrant connection closed.")

    async def init_collection(self, collection_name: str, vector_size: int = 384) -> None:
        if not self.client:
            raise RuntimeError("Qdrant client is not initialized. Call connect() first.")
        try:
            # Safely check if collection exists by calling get_collection
            try:
                await self.client.get_collection(collection_name)
                logger.info("Qdrant collection already exists.", collection_name=collection_name)
            except (UnexpectedResponse, Exception):
                logger.info("Creating new vector collection in Qdrant...", collection_name=collection_name, vector_size=vector_size)
                await self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=vector_size,
                        distance=qmodels.Distance.COSINE
                    )
                )
                logger.info("Vector collection created successfully.", collection_name=collection_name)
        except Exception as e:
            logger.error("Failed to initialize Qdrant collection", collection_name=collection_name, error=str(e))
            raise e

    async def search_similarity(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 3,
        document_id: str | None = None
    ) -> list[dict]:
        if not self.client:
            raise RuntimeError("Qdrant client is not initialized. Call connect() first.")
        
        # Build filter if document_id is specified
        search_filter = None
        if document_id:
            search_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id)
                    )
                ]
            )

        try:
            response = await self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=search_filter,
                limit=limit
            )
            
            # Convert hits to structured output
            return [
                {
                    "id": str(hit.id),
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in response.points
            ]
        except Exception as e:
            logger.error("Similarity search in Qdrant failed", collection=collection_name, error=str(e))
            raise e

    async def delete_document(self, collection_name: str, document_id: str) -> None:
        if not self.client:
            raise RuntimeError("Qdrant client is not initialized. Call connect() first.")
        try:
            logger.info("Deleting vector points in Qdrant...", collection=collection_name, document_id=document_id)
            await self.client.delete(
                collection_name=collection_name,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_id",
                                match=qmodels.MatchValue(value=document_id)
                            )
                        ]
                    )
                )
            )
            logger.info("Vector points deleted successfully in Qdrant.", collection=collection_name, document_id=document_id)
        except Exception as e:
            logger.error("Failed to delete points in Qdrant", collection=collection_name, document_id=document_id, error=str(e))
            raise e

    async def ping(self) -> bool:
        if not self.client:
            return False
        try:
            await self.client.get_collections()
            return True
        except Exception:
            return False

qdrant_service = QdrantService()

import asyncio  
# pyrefly: ignore [missing-import]
from sentence_transformers import SentenceTransformer
# pyrefly: ignore [missing-import]
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)

class EmbeddingService:
    def __init__(self):
        self.model: SentenceTransformer | None = None

    def load_model(self) -> None:
        if not self.model:
            logger.info("Loading local embedding model...", model_name=settings.EMBEDDING_MODEL_NAME)
            # Loads model. If running for the first time, this downloads from HuggingFace
            self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            logger.info("Local embedding model loaded successfully.")

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not self.model:
            # Offload heavy model load to thread
            await asyncio.to_thread(self.load_model)
        
        # Offload encoding to thread pool to keep FastAPI event loop responsive
        embeddings = await asyncio.to_thread(
            self.model.encode, 
            texts, 
            convert_to_numpy=True,
            show_progress_bar=False
        )
        return embeddings.tolist()

    async def get_embedding(self, text: str) -> list[float]:
        embeddings = await self.get_embeddings([text])
        return embeddings[0]

embedding_service = EmbeddingService()

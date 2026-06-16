# pyrefly: ignore [missing-import]
from fastapi import APIRouter
# pyrefly: ignore [missing-import]
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.search import router as search_router
from app.api.v1.chat import router as chat_router
from app.api.v1.auth import router as auth_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(ingestion_router)
router.include_router(search_router)
router.include_router(chat_router)

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Sanitize DATABASE_URL for asyncpg driver compatibility (convert sslmode= to ssl=)
def _sanitize_db_url(url: str) -> str:
    """Safely convert sslmode= query param to ssl= for asyncpg compatibility."""
    parsed = urlparse(url)
    if parsed.query and "sslmode" in parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        if "sslmode" in params:
            params["ssl"] = params.pop("sslmode")
        new_query = urlencode(params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
    return url

db_url = _sanitize_db_url(settings.DATABASE_URL)

# Create async database engine
engine = create_async_engine(
    db_url,
    echo=False,  # Set to True for debugging SQL queries
    pool_pre_ping=True,  # Check connection health before using
    pool_size=10,
    max_overflow=20
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

# Dependency provider for FastAPI routes
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


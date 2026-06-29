import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)

ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its bcrypt hash.
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error("Password verification error", error=str(e))
        return False

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Generate a JWT access token containing the payload data.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict | None:
    """
    Decode and validate a JWT access token.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.info("JWT token has expired")
        return None
    except jwt.PyJWTError as e:
        logger.warning("JWT token validation failed", error=str(e))
        return None


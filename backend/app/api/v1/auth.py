import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.models.sqlalchemy_models import User
from app.models.pydantic_models import UserCreate, UserLogin, UserResponse, TokenResponse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["User Authentication"])

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to validate the Bearer token and return the current database user.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user does not exist in system database.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user and return a JWT access token.
    """
    try:
        # Check if username already exists
        query = select(User).where(User.username == payload.username)
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already registered."
            )
        
        # Create and save user
        hashed = hash_password(payload.password)
        new_user = User(username=payload.username, hashed_password=hashed)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Create token
        token = create_access_token(data={"sub": new_user.username})
        logger.info("New user registered successfully", user_id=str(new_user.id), username=new_user.username)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": new_user
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Signup endpoint failure", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal signup failure"
        )

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate a user with credentials and return a JWT access token.
    """
    try:
        query = select(User).where(User.username == payload.username)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = create_access_token(data={"sub": user.username})
        logger.info("User logged in successfully", user_id=str(user.id), username=user.username)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login endpoint failure", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal login failure"
        )

@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Fetch current user profile.
    """
    return current_user

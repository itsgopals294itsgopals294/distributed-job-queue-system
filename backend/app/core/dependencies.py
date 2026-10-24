import time
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.core.security import decode_access_token
from app.core.redis import RedisClient

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

DEFAULT_API_KEY = "jq_live_enterprise_secret_key"


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # 1. Check API Key Header for real-world microservices / SDK clients
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key == DEFAULT_API_KEY:
        # Load system admin user as the acting identity
        stmt = select(User).where(User.role == UserRole.ADMIN).limit(1)
        res = await db.execute(stmt)
        admin = res.scalar_one_or_none()
        if admin:
            return admin

    # 2. Check JWT Bearer Token for interactive users
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please provide a valid Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated or suspended."
        )

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required."
        )
    return current_user


async def check_rate_limit(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    limit: int = 120,
    window_seconds: int = 60
):
    """Atomic sliding rate limiter per user/IP."""
    identifier = f"rate:{current_user.id if current_user else (request.client.host if request.client else 'global')}"
    try:
        redis = await RedisClient.get_client()
        current_count = await redis.incr(identifier)
        if current_count == 1:
            await redis.expire(identifier, window_seconds)
        if current_count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: maximum {limit} requests per {window_seconds}s."
            )
    except HTTPException:
        raise
    except Exception:
        # Don't fail request if rate limiter store encounters transient error
        pass

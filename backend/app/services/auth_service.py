import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest, Token
from app.core.security import hash_password, verify_password, create_access_token
from app.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower())
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def register_user(db: AsyncSession, req: RegisterRequest) -> User:
        existing = await AuthService.get_user_by_email(db, req.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        new_user = User(
            email=req.email.lower(),
            hashed_password=hash_password(req.password),
            full_name=req.full_name,
            role=UserRole.USER,
            is_active=True
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"Registered new user: {new_user.email} (ID: {new_user.id})")
        return new_user

    @staticmethod
    async def authenticate_user(db: AsyncSession, req: LoginRequest) -> Token:
        user = await AuthService.get_user_by_email(db, req.email)
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled or suspended."
            )

        token = create_access_token(subject=user.id, role=user.role.value)
        return Token(
            access_token=token,
            user_id=user.id,
            email=user.email,
            role=user.role,
            full_name=user.full_name
        )

    @staticmethod
    async def ensure_default_admin(db: AsyncSession):
        """Ensures the initial administrator account exists."""
        admin_email = settings.ADMIN_EMAIL.lower()
        admin = await AuthService.get_user_by_email(db, admin_email)
        if not admin:
            admin = User(
                email=admin_email,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                full_name="System Administrator",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Created default system administrator: {admin_email}")

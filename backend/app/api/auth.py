from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token, RegisterRequest, LoginRequest, UserResponse
from app.services.auth_service import AuthService
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    user = await AuthService.register_user(db, req)
    return user


@router.post("/login", response_model=Token)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate with JSON payload and receive JWT access token."""
    return await AuthService.authenticate_user(db, req)


@router.post("/token", response_model=Token, include_in_schema=False)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """OAuth2 compatible token login for Swagger UI."""
    req = LoginRequest(email=form_data.username, password=form_data.password)
    return await AuthService.authenticate_user(db, req)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieve current authenticated user information."""
    return current_user

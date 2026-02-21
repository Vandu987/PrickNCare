"""Authentication endpoints: login, refresh, logout — task 3.3."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.security import (
    blacklist_token,
    clear_session,
    create_access_token,
    create_refresh_token,
    revoke_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.models.users import User
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email + password and return JWT tokens."""
    result = await db.execute(
        select(User).where(User.email == data.email, User.is_active.is_(True))
    )
    user: User | None = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token, jti = create_access_token(str(user.id), user.role.value)
    refresh_token = await create_refresh_token(str(user.id), jti)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Exchange a valid refresh token for a new access + refresh token pair."""
    valid = await verify_refresh_token(data.user_id, data.jti, data.refresh_token)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    result = await db.execute(
        select(User).where(User.id == data.user_id, User.is_active.is_(True))
    )
    user: User | None = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Rotate: revoke old refresh token, issue new pair
    await revoke_refresh_token(data.user_id, data.jti)
    new_access, new_jti = create_access_token(str(user.id), user.role.value)
    new_refresh = await create_refresh_token(str(user.id), new_jti)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: LogoutRequest) -> None:
    """Blacklist the access token jti and revoke the refresh token."""
    await blacklist_token(data.jti)
    if data.refresh_token:
        await revoke_refresh_token(data.user_id, data.jti)
    await clear_session(data.user_id)

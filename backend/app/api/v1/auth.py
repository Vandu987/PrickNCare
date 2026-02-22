"""Authentication endpoints: login, OTP, refresh, logout — tasks 3.3 & 3.4."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.security import (
    blacklist_token,
    check_otp_rate_limit,
    clear_session,
    create_access_token,
    create_refresh_token,
    generate_otp,
    increment_otp_rate_limit,
    revoke_refresh_token,
    store_otp,
    verify_otp,
    verify_password,
    verify_refresh_token,
)
from app.core.sms_gateway import get_sms_provider
from app.models.users import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    OTPRequestSchema,
    OTPVerifyRequest,
    RefreshRequest,
    TokenResponse,
)

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

    # Initialize session activity so first API call doesn't fail session check
    from app.core.security import update_last_activity
    await update_last_activity(str(user.id))

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

    from app.core.security import update_last_activity
    await update_last_activity(str(user.id))

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(data: LogoutRequest) -> None:
    """Blacklist the access token jti and revoke the refresh token."""
    await blacklist_token(data.jti)
    if data.refresh_token:
        await revoke_refresh_token(data.user_id, data.jti)
    await clear_session(data.user_id)


# ---------------------------------------------------------------------------
# POST /auth/otp/request
# ---------------------------------------------------------------------------


@router.post("/otp/request", status_code=status.HTTP_200_OK)
async def otp_request(data: OTPRequestSchema) -> dict:
    """Generate and send a 6-digit OTP to the given phone number."""
    if not await check_otp_rate_limit(data.phone):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Too many OTP requests. "
                f"Limit: {settings.OTP_RATE_LIMIT_PER_HOUR}/hour."
            ),
        )

    # TODO: Replace with real SMS provider when ready
    otp = "123456"  # Hardcoded for testing
    await store_otp(data.phone, otp)
    await increment_otp_rate_limit(data.phone)

    logger.info("OTP for %s: %s (hardcoded for testing)", data.phone, otp)

    return {"message": "OTP sent successfully"}


# ---------------------------------------------------------------------------
# POST /auth/otp/verify
# ---------------------------------------------------------------------------


@router.post("/otp/verify", response_model=TokenResponse)
async def otp_verify(
    data: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Verify OTP and issue JWT tokens if valid."""
    valid = await verify_otp(data.phone, data.otp)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    result = await db.execute(
        select(User).where(User.phone == data.phone, User.is_active.is_(True))
    )
    user: User | None = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active user found for this phone number",
        )

    access_token, jti = create_access_token(str(user.id), user.role.value)
    refresh_token = await create_refresh_token(str(user.id), jti)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

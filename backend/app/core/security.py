"""Security utilities: JWT, password hashing, token blacklist, session tracking."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt as _bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.redis import redis_delete, redis_exists, redis_get, redis_set

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REFRESH_PREFIX = "refresh:"  # refresh:<user_id>:<jti> → "1"
_BLACKLIST_PREFIX = "blacklist:"  # blacklist:<jti> → "1"
_ACTIVITY_PREFIX = "activity:"  # activity:<user_id> → unix timestamp


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the bcrypt *hashed* value."""
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# Access token (JWT)
# ---------------------------------------------------------------------------


def create_access_token(user_id: str, role: str) -> tuple[str, str]:
    """Create a signed JWT access token.

    Returns (token, jti) so callers can track the jti for blacklisting.
    """
    jti = str(uuid.uuid4())
    now = datetime.now(tz=UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, jti


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT.  Raises JWTError on failure."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


# ---------------------------------------------------------------------------
# Refresh token (opaque, stored in Redis)
# ---------------------------------------------------------------------------


async def create_refresh_token(user_id: str, jti: str) -> str:
    """Generate an opaque refresh token and store it in Redis.

    Key: refresh:<user_id>:<jti>   TTL: REFRESH_TOKEN_EXPIRE_DAYS
    """
    token = secrets.token_urlsafe(64)
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86_400  # seconds
    key = f"{_REFRESH_PREFIX}{user_id}:{jti}"
    await redis_set(key, token, ex=ttl)
    return token


async def verify_refresh_token(user_id: str, jti: str, token: str) -> bool:
    """Return True only if the stored refresh token matches *token*."""
    key = f"{_REFRESH_PREFIX}{user_id}:{jti}"
    stored = await redis_get(key)
    return stored is not None and secrets.compare_digest(stored, token)


async def revoke_refresh_token(user_id: str, jti: str) -> None:
    """Delete the refresh token from Redis (used on logout)."""
    await redis_delete(f"{_REFRESH_PREFIX}{user_id}:{jti}")


# ---------------------------------------------------------------------------
# Token blacklisting (for logout of access tokens)
# ---------------------------------------------------------------------------


async def blacklist_token(jti: str) -> None:
    """Mark a JWT jti as invalid for the remainder of its lifetime."""
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    await redis_set(f"{_BLACKLIST_PREFIX}{jti}", "1", ex=ttl)


async def is_token_blacklisted(jti: str) -> bool:
    return await redis_exists(f"{_BLACKLIST_PREFIX}{jti}")


# ---------------------------------------------------------------------------
# Session timeout tracking
# ---------------------------------------------------------------------------


async def update_last_activity(user_id: str) -> None:
    """Record the current UTC timestamp as the user's last activity."""
    ttl = settings.SESSION_TIMEOUT_MINUTES * 60
    now_ts = str(int(datetime.now(tz=UTC).timestamp()))
    await redis_set(f"{_ACTIVITY_PREFIX}{user_id}", now_ts, ex=ttl)


async def is_session_expired(user_id: str) -> bool:
    """Return True if the session has timed out (no recent activity)."""
    return not await redis_exists(f"{_ACTIVITY_PREFIX}{user_id}")


async def clear_session(user_id: str) -> None:
    """Remove session activity record (called on logout)."""
    await redis_delete(f"{_ACTIVITY_PREFIX}{user_id}")


# ---------------------------------------------------------------------------
# High-level: validate incoming access token for route dependencies
# ---------------------------------------------------------------------------


async def validate_access_token(token: str) -> dict:
    """Decode token, check blacklist, check session timeout.

    Returns the decoded payload dict on success.
    Raises JWTError for any security failure.
    """
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise

    jti: str = payload.get("jti", "")
    user_id: str = payload.get("sub", "")

    if await is_token_blacklisted(jti):
        raise JWTError("Token has been revoked")

    if await is_session_expired(user_id):
        raise JWTError("Session has expired due to inactivity")

    await update_last_activity(user_id)
    return payload

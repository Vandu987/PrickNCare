"""RBAC dependency system — task 3.5.

Role hierarchy (highest → lowest privilege):
    super_admin  → full access to every endpoint
    city_admin   → manage resources within their assigned city
    client_user  → access client-facing resources
    phlebotomist → access phlebotomist-facing resources

Usage in routes::

    @router.get("/admin-only")
    async def admin_only(user: User = Depends(require_roles("super_admin"))):
        ...

    @router.get("/multi-role")
    async def multi(user: User = Depends(require_roles("super_admin", "city_admin"))):
        ...

    # Or via RoleChecker instance (useful when the set of roles is fixed):
    admin_or_city = RoleChecker("super_admin", "city_admin")

    @router.get("/city-resource")
    async def city_resource(user: User = Depends(admin_or_city)):
        ...
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import validate_access_token
from app.models.users import User, UserRole

# ---------------------------------------------------------------------------
# Bearer scheme — extracts the raw token from Authorization: Bearer <token>
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=True)

# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the JWT, verify it (blacklist + session), and load the User row.

    Raises HTTP 401 on any authentication failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = await validate_access_token(credentials.credentials)
    except JWTError:
        raise credentials_exception from None

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


# ---------------------------------------------------------------------------
# get_current_active_user
# ---------------------------------------------------------------------------


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Extend get_current_user to also enforce is_active=True.

    Raises HTTP 403 for deactivated accounts.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return user


# ---------------------------------------------------------------------------
# require_roles — factory function
# ---------------------------------------------------------------------------


def require_roles(*roles: str) -> Callable:
    """Return a FastAPI dependency that accepts users with any of *roles*.

    super_admin is always allowed regardless of the *roles* list.
    Raises HTTP 403 for insufficient permissions.
    """
    allowed: frozenset[str] = frozenset(roles) | {UserRole.SUPER_ADMIN.value}

    async def _check(
        user: User = Depends(get_current_active_user),
    ) -> User:
        if user.role.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _check


# ---------------------------------------------------------------------------
# RoleChecker — class-based alternative, useful as a reusable instance
# ---------------------------------------------------------------------------


class RoleChecker:
    """Callable dependency class for role-based access control.

    Example::

        admin_checker = RoleChecker("super_admin", "city_admin")

        @router.get("/protected")
        async def endpoint(user: User = Depends(admin_checker)):
            ...
    """

    def __init__(self, *roles: str) -> None:
        self._allowed: frozenset[str] = frozenset(roles) | {UserRole.SUPER_ADMIN.value}

    async def __call__(
        self,
        user: User = Depends(get_current_active_user),
    ) -> User:
        if user.role.value not in self._allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    @property
    def allowed_roles(self) -> frozenset[str]:
        return self._allowed

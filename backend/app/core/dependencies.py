"""Common FastAPI dependencies re-exported from one place.

Routes import from here so they don't need to know which sub-module
each dependency lives in.
"""

from app.api.deps import (
    RoleChecker,
    get_current_active_user,
    get_current_user,
    require_roles,
)
from app.core.database import get_db

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "require_roles",
    "RoleChecker",
]

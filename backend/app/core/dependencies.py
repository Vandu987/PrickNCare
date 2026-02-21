"""Common FastAPI dependencies re-exported from one place.

Routes import from here so they don't need to know which sub-module
each dependency lives in.
"""

from app.core.database import get_db

__all__ = ["get_db"]

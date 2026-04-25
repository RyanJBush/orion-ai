"""Compatibility module for older imports.

Use ``app.db.session`` + ``app.db.base`` as the canonical database interfaces.
"""

from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db

__all__ = ["Base", "SessionLocal", "engine", "get_db"]

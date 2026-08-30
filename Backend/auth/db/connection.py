"""
Deprecated — use auth.db_connection instead.
Kept for backward compatibility with migration scripts.
"""

from auth.db_connection import get_db_connection, release_db_connection, init_auth_db as init_db

__all__ = ["get_db_connection", "release_db_connection", "init_db"]

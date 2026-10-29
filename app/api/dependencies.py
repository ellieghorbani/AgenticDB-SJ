"""FastAPI dependency wiring."""

from typing import Annotated

from fastapi import Depends
from psycopg import Connection

from app.db.connection import get_db_connection
from app.db.service import QueryService


def get_query_service(
    connection: Annotated[Connection, Depends(get_db_connection)],
) -> QueryService:
    """Create a query service for the current read-only connection."""

    return QueryService(connection)

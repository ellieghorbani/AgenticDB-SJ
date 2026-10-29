"""FastAPI dependency for a short-lived, read-only PostgreSQL connection."""

from collections.abc import Generator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from app.core.config import Settings, get_settings


def get_db_connection(
    settings: Settings | None = None,
) -> Generator[Connection, None, None]:
    """Yield a read-only PostgreSQL connection and always close it.

    A connection is opened per request for the Day 5 MVP. A bounded connection
    pool can replace this dependency later without changing route contracts.
    """

    config = settings or get_settings()
    connection = psycopg.connect(
        host=config.postgres_host,
        port=config.postgres_port,
        dbname=config.postgres_db,
        user=config.postgres_user,
        password=config.postgres_password.get_secret_value(),
        connect_timeout=config.database_connect_timeout_seconds,
        application_name="agenticdb_sj_api",
        row_factory=dict_row,
    )

    try:
        # These are the first statements in the transaction. The API therefore
        # cannot modify ordinary tables, even if application code changes later.
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute(
            "SELECT set_config('statement_timeout', %s, true)",
            (str(config.database_statement_timeout_ms),),
        )
        yield connection
    finally:
        # A rollback cleanly ends the read-only transaction and discards any
        # session-local settings before closing the connection.
        try:
            connection.rollback()
        finally:
            connection.close()

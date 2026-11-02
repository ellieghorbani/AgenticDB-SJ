"""FastAPI dependency for a short-lived, read-only PostgreSQL connection."""

from collections.abc import Generator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from app.core.config import Settings, get_settings


def open_db_connection(settings: Settings) -> Connection:
    """Open one configured PostgreSQL connection.

    Keeping this helper separate makes connection creation directly testable while
    ensuring FastAPI does not interpret a ``Settings`` argument as request data.
    """

    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        connect_timeout=settings.database_connect_timeout_seconds,
        application_name="agenticdb_sj_api",
        row_factory=dict_row,
    )


def get_db_connection() -> Generator[Connection, None, None]:
    """Yield a read-only PostgreSQL connection and always close it."""

    config = get_settings()
    connection = open_db_connection(config)

    try:
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute(
            "SELECT set_config('statement_timeout', %s, true)",
            (str(config.database_statement_timeout_ms),),
        )
        yield connection
    finally:
        try:
            connection.rollback()
        finally:
            connection.close()

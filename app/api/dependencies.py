"""FastAPI dependency wiring."""

from typing import Annotated

from fastapi import Depends
from psycopg import Connection

from app.core.config import Settings, get_settings
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import SchemaCatalogService
from app.copilot.sql_execution import (
    CopilotExecutionService,
    ReadOnlySQLExecutor,
    SQLValidationService,
)
from app.copilot.sql_generator import TemplateSQLGenerator
from app.copilot.sql_validator import SQLASTValidator
from app.db.connection import get_db_connection
from app.db.service import QueryService


def get_query_service(
    connection: Annotated[Connection, Depends(get_db_connection)],
) -> QueryService:
    """Create a query service for the current read-only connection."""

    return QueryService(connection)


def get_schema_catalog_service(
    connection: Annotated[Connection, Depends(get_db_connection)],
) -> SchemaCatalogService:
    """Create a schema catalog service for the current read-only connection."""

    return SchemaCatalogService(connection)


def get_planner_service(
    catalog_service: Annotated[
        SchemaCatalogService,
        Depends(get_schema_catalog_service),
    ],
) -> RuleBasedQueryPlanner:
    """Create the deterministic Day 6 planner over the actual allowlisted schema."""

    return RuleBasedQueryPlanner(catalog_service.catalog())


def get_sql_generator_service(
    planner: Annotated[RuleBasedQueryPlanner, Depends(get_planner_service)],
) -> TemplateSQLGenerator:
    """Create the Day 7 non-executing SQL generator."""

    return TemplateSQLGenerator(planner)


def get_sql_validator_service(
    generator: Annotated[TemplateSQLGenerator, Depends(get_sql_generator_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SQLASTValidator:
    """Create the independent Day 8 SQLGlot AST validator."""

    return SQLASTValidator(
        generator.catalog,
        max_result_rows=settings.copilot_max_result_rows,
    )


def get_sql_validation_service(
    generator: Annotated[TemplateSQLGenerator, Depends(get_sql_generator_service)],
    validator: Annotated[SQLASTValidator, Depends(get_sql_validator_service)],
) -> SQLValidationService:
    """Create the generate-then-validate orchestration service."""

    return SQLValidationService(generator, validator)


def get_copilot_execution_service(
    generator: Annotated[TemplateSQLGenerator, Depends(get_sql_generator_service)],
    validator: Annotated[SQLASTValidator, Depends(get_sql_validator_service)],
    connection: Annotated[Connection, Depends(get_db_connection)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CopilotExecutionService:
    """Create controlled execution over the request's read-only connection."""

    executor = ReadOnlySQLExecutor(connection, settings)
    return CopilotExecutionService(generator, validator, executor, settings)

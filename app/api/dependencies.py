"""FastAPI dependency wiring."""

from typing import Annotated

from fastapi import Depends
from psycopg import Connection

from app.core.config import Settings, get_settings
from app.copilot.agent_orchestrator import AgentOrchestrator, LazyReadOnlySQLExecutor
from app.copilot.answer_synthesis import DeterministicAnswerSynthesizer
from app.copilot.embeddings import EmbeddingProvider, cached_embedding_provider
from app.copilot.vector_orchestrator import VectorAgentOrchestrator
from app.copilot.vector_router import DeterministicVectorRouter
from app.copilot.vector_search import VectorSearchService
from app.copilot.planner import RuleBasedQueryPlanner
from app.copilot.schema_catalog import SchemaCatalogService, build_static_catalog
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

def get_agent_orchestrator(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentOrchestrator:
    """Create a lazy Day 9 agent; blocked routes never open PostgreSQL."""

    catalog = build_static_catalog()
    planner = RuleBasedQueryPlanner(catalog)
    return AgentOrchestrator(
        planner=planner,
        generator=TemplateSQLGenerator(planner),
        validator=SQLASTValidator(
            catalog,
            max_result_rows=settings.copilot_max_result_rows,
        ),
        executor=LazyReadOnlySQLExecutor(settings),
        synthesizer=DeterministicAnswerSynthesizer(),
        settings=settings,
    )



def get_vector_router() -> DeterministicVectorRouter:
    """Create the deterministic Day 10 semantic/hybrid router."""

    return DeterministicVectorRouter()


def get_embedding_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmbeddingProvider:
    """Return one process-cached local embedding model."""

    return cached_embedding_provider(
        settings.embedding_model_name,
        settings.embedding_dimensions,
        settings.embedding_device,
        settings.embedding_batch_size,
    )


def get_vector_search_service(
    connection: Annotated[Connection, Depends(get_db_connection)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedder: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> VectorSearchService:
    """Create a read-only pgvector search service."""

    return VectorSearchService(connection, settings, embedder)


def get_vector_orchestrator(
    vector_router: Annotated[DeterministicVectorRouter, Depends(get_vector_router)],
    search_service: Annotated[VectorSearchService, Depends(get_vector_search_service)],
) -> VectorAgentOrchestrator:
    """Create the Day 10 vector-search workflow."""

    return VectorAgentOrchestrator(vector_router, search_service)

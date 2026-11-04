"""Day 8 SQL validation and controlled execution endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_copilot_execution_service,
    get_sql_validation_service,
)
from app.copilot.sql_execution import (
    CopilotExecutionService,
    SQLValidationService,
)
from app.models.sql_execution import (
    SQLExecutionRequest,
    SQLExecutionResponse,
    SQLValidationRequest,
    SQLValidationResponse,
)

router = APIRouter(prefix="/api/v1/copilot", tags=["copilot"])


@router.post("/validate", response_model=SQLValidationResponse)
def validate_generated_sql(
    request: SQLValidationRequest,
    service: Annotated[SQLValidationService, Depends(get_sql_validation_service)],
) -> SQLValidationResponse:
    """Generate SQL and independently validate its PostgreSQL AST."""

    return service.validate(request.question, top_k=request.top_k)


@router.post("/execute", response_model=SQLExecutionResponse)
def execute_validated_sql(
    request: SQLExecutionRequest,
    service: Annotated[CopilotExecutionService, Depends(get_copilot_execution_service)],
) -> SQLExecutionResponse:
    """Execute only SQL that passes every Day 8 policy check."""

    return service.execute(request.question, top_k=request.top_k)

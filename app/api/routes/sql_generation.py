"""Day 7 deterministic SQL-generation endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_sql_generator_service
from app.copilot.sql_generator import TemplateSQLGenerator
from app.models.sql_generation import SQLGenerationRequest, SQLGenerationResponse

router = APIRouter(prefix="/api/v1/copilot", tags=["copilot"])


@router.post("/sql", response_model=SQLGenerationResponse)
def generate_sql(
    request: SQLGenerationRequest,
    generator: Annotated[TemplateSQLGenerator, Depends(get_sql_generator_service)],
) -> SQLGenerationResponse:
    """Generate reviewed parameterized SQL but never execute it."""

    return generator.generate(request.question, top_k=request.top_k)

"""Static tool registry exposed by the Day 9 agent."""

from app.models.agent import (
    AgentToolCatalogResponse,
    AgentToolDescriptor,
    AgentToolName,
)


_TOOL_DESCRIPTORS = [
    AgentToolDescriptor(
        name=AgentToolName.query_plan,
        stage="planning",
        description=(
            "Retrieve allowlisted schema context and create a typed, non-executable "
            "query plan from the natural-language question."
        ),
        database_access=False,
        safety_boundary="Unsafe and unsupported requests are identified before SQL exists.",
    ),
    AgentToolDescriptor(
        name=AgentToolName.route_select,
        stage="routing",
        description=(
            "Choose the supported relational/spatial SQL route or stop the workflow "
            "for unsafe, unsupported, or ambiguous requests."
        ),
        database_access=False,
        safety_boundary="Only supported typed plans may enter SQL generation.",
    ),
    AgentToolDescriptor(
        name=AgentToolName.sql_generate,
        stage="generation",
        description="Convert the approved plan into reviewed parameterized PostgreSQL/PostGIS SQL.",
        database_access=False,
        safety_boundary="Raw user SQL is never accepted and generated SQL is not yet executable.",
    ),
    AgentToolDescriptor(
        name=AgentToolName.sql_validate,
        stage="validation",
        description="Reparse generated SQL with SQLGlot and apply independent AST policy checks.",
        database_access=False,
        safety_boundary="Only one bounded allowlisted SELECT statement can receive permission.",
    ),
    AgentToolDescriptor(
        name=AgentToolName.sql_execute,
        stage="execution",
        description="Execute approved SQL in a timeout-bounded read-only transaction.",
        database_access=True,
        safety_boundary="Execution assumes the restricted agenticdb_reader database role.",
    ),
    AgentToolDescriptor(
        name=AgentToolName.answer_synthesize,
        stage="answering",
        description="Create a deterministic answer and attach supporting database rows.",
        database_access=False,
        safety_boundary="The answer is derived only from the plan and returned database rows.",
    ),
]


def build_agent_tool_catalog() -> AgentToolCatalogResponse:
    """Return the fixed Day 9 tool registry."""

    return AgentToolCatalogResponse(
        tool_count=len(_TOOL_DESCRIPTORS),
        tools=list(_TOOL_DESCRIPTORS),
    )

"""Typed contracts for schema retrieval and structured query planning."""

from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from app.models.api import APIModel


class SchemaColumn(APIModel):
    name: str
    data_type: str
    nullable: bool
    description: str
    semantic_tags: list[str] = Field(default_factory=list)


class SchemaRelation(APIModel):
    qualified_name: str
    schema_name: str
    relation_name: str
    relation_type: Literal["BASE TABLE", "VIEW"]
    available: bool
    description: str
    aliases: list[str]
    primary_key_columns: list[str]
    geometry_column: str | None = None
    columns: list[SchemaColumn]


class SchemaJoin(APIModel):
    left_relation: str
    right_relation: str
    join_condition: str
    relationship: str
    description: str


class SchemaCatalogResponse(APIModel):
    generated_from: Literal["curated_allowlist+information_schema", "static_registry"]
    relation_count: int
    relations: list[SchemaRelation]
    joins: list[SchemaJoin]


class SchemaContextRequest(APIModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)


class RetrievedRelation(APIModel):
    relation: SchemaRelation
    relevance_score: float = Field(ge=0)
    matched_terms: list[str]


class SchemaContextResponse(APIModel):
    question: str
    relations: list[RetrievedRelation]
    joins: list[SchemaJoin]


class QueryType(str, Enum):
    aggregate = "aggregate"
    spatial = "spatial"
    hybrid = "hybrid"
    unsupported = "unsupported"


class PlannerIntent(str, Enum):
    schools_per_neighborhood = "schools_per_neighborhood"
    open_parks_per_neighborhood = "open_parks_per_neighborhood"
    elementary_schools_near_open_parks = "elementary_schools_near_open_parks"
    nearest_open_park_per_school = "nearest_open_park_per_school"
    open_parks_intersecting_neighborhood = "open_parks_intersecting_neighborhood"
    neighborhoods_with_minimum_schools_and_parks = (
        "neighborhoods_with_minimum_schools_and_parks"
    )
    schools_without_nearby_open_park = "schools_without_nearby_open_park"
    average_nearest_park_distance_by_neighborhood = (
        "average_nearest_park_distance_by_neighborhood"
    )
    open_parks_with_most_nearby_schools = "open_parks_with_most_nearby_schools"
    neighborhoods_with_elementary_and_high_schools = (
        "neighborhoods_with_elementary_and_high_schools"
    )
    unsafe_request = "unsafe_request"
    unsupported = "unsupported"


class FilterOperator(str, Enum):
    eq = "eq"
    neq = "neq"
    gte = "gte"
    lte = "lte"
    in_ = "in"
    is_null = "is_null"
    not_exists = "not_exists"


class PlanFilter(APIModel):
    field: str
    operator: FilterOperator
    value: str | int | float | list[str] | None = None


class SpatialRelationship(str, Enum):
    within_distance = "within_distance"
    nearest = "nearest"
    intersects = "intersects"
    contains = "contains"


class SpatialConstraint(APIModel):
    relationship: SpatialRelationship
    left_relation: str
    right_relation: str
    distance_meters: float | None = Field(default=None, gt=0)
    negated: bool = False

    @model_validator(mode="after")
    def validate_distance(self) -> "SpatialConstraint":
        if (
            self.relationship == SpatialRelationship.within_distance
            and self.distance_meters is None
        ):
            raise ValueError("within_distance requires distance_meters")
        return self


class SortDirection(str, Enum):
    asc = "asc"
    desc = "desc"


class PlanSort(APIModel):
    field: str
    direction: SortDirection


class QueryPlan(APIModel):
    question: str
    intent: PlannerIntent
    query_type: QueryType
    confidence: float = Field(ge=0, le=1)
    relations: list[str]
    select_fields: list[str]
    filters: list[PlanFilter] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    sort: list[PlanSort] = Field(default_factory=list)
    spatial_constraint: SpatialConstraint | None = None
    limit: int | None = Field(default=None, ge=1, le=1000)
    steps: list[str]
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requires_clarification: bool = False
    execution_allowed: Literal[False] = False
    sql_generated: Literal[False] = False

    @model_validator(mode="after")
    def validate_plan_shape(self) -> "QueryPlan":
        if self.query_type in {QueryType.spatial, QueryType.hybrid}:
            spatial_optional_intents = {
                PlannerIntent.neighborhoods_with_minimum_schools_and_parks,
                PlannerIntent.neighborhoods_with_elementary_and_high_schools,
            }
            if (
                self.spatial_constraint is None
                and self.intent not in spatial_optional_intents
            ):
                raise ValueError("spatial and hybrid plans require a spatial constraint")
        if self.query_type == QueryType.unsupported and self.execution_allowed:
            raise ValueError("unsupported plans cannot be executable")
        return self


class PlanRequest(APIModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=6, ge=1, le=10)


class PlanResponse(APIModel):
    planner: Literal["rule_based_day6"]
    plan: QueryPlan
    schema_context: SchemaContextResponse

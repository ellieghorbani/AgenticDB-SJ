"""Deterministic Day 7 SQL generation over validated Day 6 plans.

The generator deliberately does not execute SQL. It converts one of the ten
supported planner intents into a reviewed PostgreSQL/PostGIS template, binds
all variable values as parameters, and validates the generated artifact against
the curated schema catalog.
"""

from dataclasses import dataclass
import re
from textwrap import dedent
from typing import Callable

from app.copilot.planner import RuleBasedQueryPlanner
from app.models.copilot import FilterOperator, PlannerIntent, QueryPlan, QueryType
from app.models.sql_generation import (
    SQLGenerationResponse,
    SQLGenerationStatus,
    SQLParameter,
    SQLSafetyCheck,
)


_FORBIDDEN_WORDS = {
    "insert", "update", "delete", "drop", "alter", "truncate", "create",
    "grant", "revoke", "copy", "vacuum", "merge", "call", "do",
}
_RELATION_PATTERN = re.compile(r"\b(?:core|app)\.[a-z_][a-z0-9_]*\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class TemplateOutput:
    sql: str
    parameters: tuple[SQLParameter, ...]
    relations: tuple[str, ...]
    source_columns: tuple[str, ...]


class TemplateSQLGenerator:
    """Generate reviewed, parameterized SQL for supported planner intents."""

    generator_name = "template_sql_day7"

    def __init__(self, planner: RuleBasedQueryPlanner):
        self.planner = planner
        self.catalog = planner.catalog
        self._relation_lookup = {
            relation.qualified_name: relation for relation in self.catalog.relations
        }
        self._builders: dict[PlannerIntent, Callable[[QueryPlan], TemplateOutput]] = {
            PlannerIntent.schools_per_neighborhood: self._schools_per_neighborhood,
            PlannerIntent.open_parks_per_neighborhood: self._open_parks_per_neighborhood,
            PlannerIntent.elementary_schools_near_open_parks: self._elementary_schools_near_parks,
            PlannerIntent.nearest_open_park_per_school: self._nearest_open_park_per_school,
            PlannerIntent.open_parks_intersecting_neighborhood: self._parks_intersecting_neighborhood,
            PlannerIntent.neighborhoods_with_minimum_schools_and_parks: self._neighborhood_minimums,
            PlannerIntent.schools_without_nearby_open_park: self._schools_without_nearby_park,
            PlannerIntent.average_nearest_park_distance_by_neighborhood: self._average_nearest_distance,
            PlannerIntent.open_parks_with_most_nearby_schools: self._parks_with_most_schools,
            PlannerIntent.neighborhoods_with_elementary_and_high_schools: self._neighborhoods_with_both_levels,
        }

    def generate(self, question: str, top_k: int = 6) -> SQLGenerationResponse:
        plan_response = self.planner.plan(question, top_k=top_k)
        plan = plan_response.plan

        if plan.intent in {PlannerIntent.unsafe_request, PlannerIntent.unsupported}:
            warning = (
                "Unsafe requests are blocked before SQL generation."
                if plan.intent == PlannerIntent.unsafe_request
                else "The request is outside the supported Day 7 SQL templates."
            )
            return self._blocked_response(
                plan,
                SQLGenerationStatus.blocked,
                [warning, *plan.warnings],
                check_name="supported_intent",
            )

        if plan.requires_clarification:
            return self._blocked_response(
                plan,
                SQLGenerationStatus.requires_clarification,
                [
                    "The planner requires clarification before SQL can be generated.",
                    *plan.warnings,
                ],
                check_name="clarification_resolved",
            )

        builder = self._builders.get(plan.intent)
        if builder is None:
            return self._blocked_response(
                plan,
                SQLGenerationStatus.blocked,
                ["No reviewed SQL template exists for this intent."],
                check_name="template_available",
            )

        output = builder(plan)
        checks = self._validate(plan, output)
        if not all(check.passed for check in checks):
            return SQLGenerationResponse(
                generator=self.generator_name,
                planner="rule_based_day6",
                question=plan.question,
                intent=plan.intent,
                query_type=plan.query_type,
                status=SQLGenerationStatus.blocked,
                plan=plan,
                sql=None,
                statement_type="NONE",
                parameters=[],
                relations=list(output.relations),
                source_columns=list(output.source_columns),
                safety_checks=checks,
                warnings=["Generated SQL failed an internal Day 7 safety check."],
                execution_allowed=False,
                sql_generated=False,
            )

        statement_type = output.sql.lstrip().split(maxsplit=1)[0].upper()
        return SQLGenerationResponse(
            generator=self.generator_name,
            planner="rule_based_day6",
            question=plan.question,
            intent=plan.intent,
            query_type=plan.query_type,
            status=SQLGenerationStatus.generated,
            plan=plan,
            sql=output.sql,
            statement_type=statement_type,
            parameters=list(output.parameters),
            relations=list(output.relations),
            source_columns=list(output.source_columns),
            safety_checks=checks,
            warnings=list(plan.warnings),
            execution_allowed=False,
            sql_generated=True,
        )

    def _blocked_response(
        self,
        plan: QueryPlan,
        status: SQLGenerationStatus,
        warnings: list[str],
        *,
        check_name: str,
    ) -> SQLGenerationResponse:
        return SQLGenerationResponse(
            generator=self.generator_name,
            planner="rule_based_day6",
            question=plan.question,
            intent=plan.intent,
            query_type=plan.query_type,
            status=status,
            plan=plan,
            sql=None,
            statement_type="NONE",
            parameters=[],
            relations=[],
            source_columns=[],
            safety_checks=[
                SQLSafetyCheck(
                    name=check_name,
                    passed=False,
                    detail=warnings[0],
                )
            ],
            warnings=warnings,
            execution_allowed=False,
            sql_generated=False,
        )

    def _validate(self, plan: QueryPlan, output: TemplateOutput) -> list[SQLSafetyCheck]:
        sql = output.sql.strip()
        normalized = re.sub(r"\s+", " ", sql.lower())
        statement_type = normalized.split(maxsplit=1)[0] if normalized else ""
        internal_semicolons = ";" in sql.rstrip().rstrip(";")
        forbidden = sorted(
            word for word in _FORBIDDEN_WORDS
            if re.search(rf"\b{re.escape(word)}\b", normalized)
        )
        actual_relations = sorted(set(_RELATION_PATTERN.findall(sql)))
        actual_relations = [relation.lower() for relation in actual_relations]
        declared_relations = sorted(set(output.relations))
        allowed_relations = set(self._relation_lookup)

        invalid_columns: list[str] = []
        for reference in output.source_columns:
            relation_name, column_name = reference.rsplit(".", maxsplit=1)
            relation = self._relation_lookup.get(relation_name)
            if relation is None or column_name not in {col.name for col in relation.columns}:
                invalid_columns.append(reference)

        plan_relations = set(plan.relations)
        output_relations = set(output.relations)

        return [
            SQLSafetyCheck(
                name="supported_intent",
                passed=plan.intent in self._builders,
                detail="The plan intent has a reviewed deterministic template.",
            ),
            SQLSafetyCheck(
                name="read_only_statement",
                passed=statement_type in {"select", "with"},
                detail=f"Statement begins with {statement_type.upper() or 'NONE'}.",
            ),
            SQLSafetyCheck(
                name="single_statement",
                passed=not internal_semicolons,
                detail="Only one SQL statement is present.",
            ),
            SQLSafetyCheck(
                name="forbidden_keywords",
                passed=not forbidden,
                detail=(
                    "No write or administrative SQL keywords were found."
                    if not forbidden
                    else f"Forbidden keywords found: {', '.join(forbidden)}"
                ),
            ),
            SQLSafetyCheck(
                name="parameter_count",
                passed=sql.count("%s") == len(output.parameters),
                detail=(
                    f"{sql.count('%s')} placeholders and "
                    f"{len(output.parameters)} parameter values."
                ),
            ),
            SQLSafetyCheck(
                name="relations_allowlisted",
                passed=(
                    output_relations.issubset(allowed_relations)
                    and actual_relations == declared_relations
                ),
                detail=(
                    "All SQL relations are declared and allowlisted."
                    if output_relations.issubset(allowed_relations)
                    and actual_relations == declared_relations
                    else (
                        f"SQL relations={actual_relations}; "
                        f"declared={declared_relations}."
                    )
                ),
            ),
            SQLSafetyCheck(
                name="source_columns_allowlisted",
                passed=not invalid_columns,
                detail=(
                    "All declared source columns exist in the curated catalog."
                    if not invalid_columns
                    else f"Invalid source columns: {', '.join(invalid_columns)}"
                ),
            ),
            SQLSafetyCheck(
                name="plan_relations_covered",
                passed=plan_relations.issubset(output_relations),
                detail="Generated SQL covers every relation required by the plan.",
            ),
            SQLSafetyCheck(
                name="bounded_result",
                passed=" limit " in f" {normalized} ",
                detail="The generated query contains an explicit LIMIT.",
            ),
            SQLSafetyCheck(
                name="execution_disabled",
                passed=plan.execution_allowed is False,
                detail="Day 7 generation never grants execution permission.",
            ),
        ]

    @staticmethod
    def _parameter(
        position: int,
        name: str,
        value: str | int | float | bool,
        pg_type: str,
    ) -> SQLParameter:
        return SQLParameter(
            position=position,
            name=name,
            value=value,
            pg_type=pg_type,
        )

    @staticmethod
    def _filter_value(
        plan: QueryPlan,
        field: str,
        *,
        operator: FilterOperator | None = None,
    ):
        for item in plan.filters:
            if item.field == field and (operator is None or item.operator == operator):
                return item.value
        raise ValueError(f"Required plan filter was not found: {field}")

    @staticmethod
    def _clean(sql: str) -> str:
        return dedent(sql).strip().rstrip(";")

    def _schools_per_neighborhood(self, plan: QueryPlan) -> TemplateOutput:
        del plan
        return TemplateOutput(
            sql=self._clean("""
                SELECT
                    n.enterprise_id AS neighborhood_id,
                    n.neighborhood_name,
                    COUNT(DISTINCT sn.cds_code)::integer AS active_school_count
                FROM core.neighborhoods AS n
                LEFT JOIN app.school_neighborhoods AS sn
                    ON sn.neighborhood_id = n.enterprise_id
                GROUP BY n.enterprise_id, n.neighborhood_name
                ORDER BY active_school_count DESC, n.neighborhood_name, n.enterprise_id
                LIMIT 1000
            """),
            parameters=(),
            relations=("app.school_neighborhoods", "core.neighborhoods"),
            source_columns=(
                "core.neighborhoods.enterprise_id",
                "core.neighborhoods.neighborhood_name",
                "app.school_neighborhoods.neighborhood_id",
                "app.school_neighborhoods.cds_code",
            ),
        )

    def _open_parks_per_neighborhood(self, plan: QueryPlan) -> TemplateOutput:
        del plan
        return TemplateOutput(
            sql=self._clean("""
                SELECT
                    n.enterprise_id AS neighborhood_id,
                    n.neighborhood_name,
                    COUNT(DISTINCT op.facility_id)::integer AS open_park_feature_count
                FROM core.neighborhoods AS n
                LEFT JOIN app.open_park_neighborhood_intersections AS op
                    ON op.neighborhood_id = n.enterprise_id
                GROUP BY n.enterprise_id, n.neighborhood_name
                ORDER BY open_park_feature_count DESC, n.neighborhood_name, n.enterprise_id
                LIMIT 1000
            """),
            parameters=(),
            relations=(
                "app.open_park_neighborhood_intersections",
                "core.neighborhoods",
            ),
            source_columns=(
                "core.neighborhoods.enterprise_id",
                "core.neighborhoods.neighborhood_name",
                "app.open_park_neighborhood_intersections.neighborhood_id",
                "app.open_park_neighborhood_intersections.facility_id",
            ),
        )

    def _elementary_schools_near_parks(self, plan: QueryPlan) -> TemplateOutput:
        distance = plan.spatial_constraint.distance_meters  # type: ignore[union-attr]
        school_level = self._filter_value(
            plan,
            "app.san_jose_active_schools_spatial.education_level_code",
        )
        park_status = self._filter_value(plan, "core.parks.current_status")
        return TemplateOutput(
            sql=self._clean("""
                SELECT
                    s.cds_code,
                    s.school_name,
                    s.district_name,
                    s.neighborhood_id,
                    s.neighborhood_name,
                    nearest.facility_id AS nearest_open_park_id,
                    nearest.park_name AS nearest_open_park_name,
                    nearest.park_type_code,
                    nearest.park_class_code,
                    ROUND(nearest.distance_meters::numeric, 2) AS distance_meters,
                    ROUND((nearest.distance_meters / 1609.344)::numeric, 4) AS distance_miles
                FROM app.san_jose_active_schools_spatial AS s
                CROSS JOIN LATERAL (
                    SELECT
                        p.facility_id,
                        p.park_name,
                        p.park_type_code,
                        p.park_class_code,
                        ST_Distance(s.geom::geography, p.geom::geography) AS distance_meters
                    FROM core.parks AS p
                    WHERE p.current_status = %s
                      AND ST_DWithin(s.geom::geography, p.geom::geography, %s)
                    ORDER BY ST_Distance(s.geom::geography, p.geom::geography), p.facility_id
                    LIMIT 1
                ) AS nearest
                WHERE s.education_level_code = %s
                ORDER BY nearest.distance_meters, s.school_name, s.cds_code
                LIMIT 1000
            """),
            parameters=(
                self._parameter(1, "park_status", str(park_status), "text"),
                self._parameter(2, "distance_meters", float(distance), "double precision"),
                self._parameter(3, "education_level_code", str(school_level), "text"),
            ),
            relations=("app.san_jose_active_schools_spatial", "core.parks"),
            source_columns=(
                "app.san_jose_active_schools_spatial.cds_code",
                "app.san_jose_active_schools_spatial.school_name",
                "app.san_jose_active_schools_spatial.district_name",
                "app.san_jose_active_schools_spatial.neighborhood_id",
                "app.san_jose_active_schools_spatial.neighborhood_name",
                "app.san_jose_active_schools_spatial.education_level_code",
                "app.san_jose_active_schools_spatial.geom",
                "core.parks.facility_id",
                "core.parks.park_name",
                "core.parks.park_type_code",
                "core.parks.park_class_code",
                "core.parks.current_status",
                "core.parks.geom",
            ),
        )

    def _nearest_open_park_per_school(self, plan: QueryPlan) -> TemplateOutput:
        park_status = self._filter_value(plan, "core.parks.current_status")
        return TemplateOutput(
            sql=self._clean("""
                SELECT
                    s.cds_code,
                    s.school_name,
                    s.district_name,
                    s.education_level_code,
                    s.education_level_name,
                    s.neighborhood_id,
                    s.neighborhood_name,
                    nearest.facility_id AS nearest_open_park_id,
                    nearest.park_name AS nearest_open_park_name,
                    nearest.park_type_code,
                    nearest.park_class_code,
                    ROUND(nearest.distance_meters::numeric, 2) AS distance_meters,
                    ROUND((nearest.distance_meters / 1609.344)::numeric, 4) AS distance_miles
                FROM app.san_jose_active_schools_spatial AS s
                CROSS JOIN LATERAL (
                    SELECT
                        p.facility_id,
                        p.park_name,
                        p.park_type_code,
                        p.park_class_code,
                        ST_Distance(s.geom::geography, p.geom::geography) AS distance_meters
                    FROM core.parks AS p
                    WHERE p.current_status = %s
                      AND ST_DWithin(
                          s.geom::geography,
                          p.geom::geography,
                          1609.344
                      )
                    ORDER BY ST_Distance(s.geom::geography, p.geom::geography), p.facility_id
                    LIMIT 1
                ) AS nearest
                ORDER BY nearest.distance_meters, s.school_name, s.cds_code
                LIMIT 1000
            """),
            parameters=(self._parameter(1, "park_status", str(park_status), "text"),),
            relations=("app.san_jose_active_schools_spatial", "core.parks"),
            source_columns=(
                "app.san_jose_active_schools_spatial.cds_code",
                "app.san_jose_active_schools_spatial.school_name",
                "app.san_jose_active_schools_spatial.district_name",
                "app.san_jose_active_schools_spatial.education_level_code",
                "app.san_jose_active_schools_spatial.education_level_name",
                "app.san_jose_active_schools_spatial.neighborhood_id",
                "app.san_jose_active_schools_spatial.neighborhood_name",
                "app.san_jose_active_schools_spatial.geom",
                "core.parks.facility_id",
                "core.parks.park_name",
                "core.parks.park_type_code",
                "core.parks.park_class_code",
                "core.parks.current_status",
                "core.parks.geom",
            ),
        )

    def _parks_intersecting_neighborhood(self, plan: QueryPlan) -> TemplateOutput:
        neighborhood_name = self._filter_value(
            plan,
            "app.open_park_neighborhood_intersections.neighborhood_name",
        )
        return TemplateOutput(
            sql=self._clean("""
                SELECT
                    op.neighborhood_id,
                    op.neighborhood_name,
                    op.facility_id,
                    op.park_name,
                    op.park_type_code,
                    op.park_class_code,
                    ROUND(op.intersection_area_m2::numeric, 2) AS intersection_area_m2
                FROM app.open_park_neighborhood_intersections AS op
                WHERE LOWER(op.neighborhood_name) = LOWER(%s)
                ORDER BY op.intersection_area_m2 DESC, op.park_name, op.facility_id
                LIMIT 1000
            """),
            parameters=(
                self._parameter(1, "neighborhood_name", str(neighborhood_name), "text"),
            ),
            relations=("app.open_park_neighborhood_intersections",),
            source_columns=(
                "app.open_park_neighborhood_intersections.neighborhood_id",
                "app.open_park_neighborhood_intersections.neighborhood_name",
                "app.open_park_neighborhood_intersections.facility_id",
                "app.open_park_neighborhood_intersections.park_name",
                "app.open_park_neighborhood_intersections.park_type_code",
                "app.open_park_neighborhood_intersections.park_class_code",
                "app.open_park_neighborhood_intersections.intersection_area_m2",
            ),
        )

    def _neighborhood_minimums(self, plan: QueryPlan) -> TemplateOutput:
        school_minimum = self._filter_value(
            plan,
            "active_school_count",
            operator=FilterOperator.gte,
        )
        park_minimum = self._filter_value(
            plan,
            "open_park_feature_count",
            operator=FilterOperator.gte,
        )
        return TemplateOutput(
            sql=self._clean("""
                WITH school_counts AS (
                    SELECT
                        n.enterprise_id AS neighborhood_id,
                        COUNT(DISTINCT sn.cds_code)::integer AS active_school_count
                    FROM core.neighborhoods AS n
                    LEFT JOIN app.school_neighborhoods AS sn
                        ON sn.neighborhood_id = n.enterprise_id
                    GROUP BY n.enterprise_id
                ),
                park_counts AS (
                    SELECT
                        n.enterprise_id AS neighborhood_id,
                        COUNT(DISTINCT op.facility_id)::integer AS open_park_feature_count
                    FROM core.neighborhoods AS n
                    LEFT JOIN app.open_park_neighborhood_intersections AS op
                        ON op.neighborhood_id = n.enterprise_id
                    GROUP BY n.enterprise_id
                )
                SELECT
                    n.enterprise_id AS neighborhood_id,
                    n.neighborhood_name,
                    sc.active_school_count,
                    pc.open_park_feature_count
                FROM core.neighborhoods AS n
                JOIN school_counts AS sc ON sc.neighborhood_id = n.enterprise_id
                JOIN park_counts AS pc ON pc.neighborhood_id = n.enterprise_id
                WHERE sc.active_school_count >= %s
                  AND pc.open_park_feature_count >= %s
                ORDER BY sc.active_school_count DESC,
                         pc.open_park_feature_count DESC,
                         n.neighborhood_name,
                         n.enterprise_id
                LIMIT 1000
            """),
            parameters=(
                self._parameter(1, "minimum_school_count", int(school_minimum), "integer"),
                self._parameter(2, "minimum_park_count", int(park_minimum), "integer"),
            ),
            relations=(
                "app.open_park_neighborhood_intersections",
                "app.school_neighborhoods",
                "core.neighborhoods",
            ),
            source_columns=(
                "core.neighborhoods.enterprise_id",
                "core.neighborhoods.neighborhood_name",
                "app.school_neighborhoods.neighborhood_id",
                "app.school_neighborhoods.cds_code",
                "app.open_park_neighborhood_intersections.neighborhood_id",
                "app.open_park_neighborhood_intersections.facility_id",
            ),
        )

    def _schools_without_nearby_park(self, plan: QueryPlan) -> TemplateOutput:
        distance = plan.spatial_constraint.distance_meters  # type: ignore[union-attr]
        park_status = self._filter_value(plan, "core.parks.current_status")
        return TemplateOutput(
            sql=self._clean("""
                SELECT
                    s.cds_code,
                    s.school_name,
                    s.district_name,
                    s.education_level_code,
                    s.neighborhood_id,
                    s.neighborhood_name,
                    nearest.facility_id AS nearest_open_park_id,
                    nearest.park_name AS nearest_open_park_name,
                    ROUND(nearest.distance_meters::numeric, 2) AS distance_meters,
                    ROUND((nearest.distance_meters / 1609.344)::numeric, 4) AS distance_miles
                FROM app.san_jose_active_schools_spatial AS s
                LEFT JOIN LATERAL (
                    SELECT
                        p.facility_id,
                        p.park_name,
                        ST_Distance(s.geom::geography, p.geom::geography) AS distance_meters
                    FROM core.parks AS p
                    WHERE p.current_status = %s
                      AND ST_DWithin(
                          s.geom::geography,
                          p.geom::geography,
                          %s
                      )
                    ORDER BY ST_Distance(s.geom::geography, p.geom::geography), p.facility_id
                    LIMIT 1
                ) AS nearest ON TRUE
                WHERE nearest.facility_id IS NULL
                ORDER BY s.school_name, s.cds_code
                LIMIT 1000
            """),
            parameters=(
                self._parameter(1, "park_status", str(park_status), "text"),
                self._parameter(2, "distance_meters", float(distance), "double precision"),
            ),
            relations=("app.san_jose_active_schools_spatial", "core.parks"),
            source_columns=(
                "app.san_jose_active_schools_spatial.cds_code",
                "app.san_jose_active_schools_spatial.school_name",
                "app.san_jose_active_schools_spatial.district_name",
                "app.san_jose_active_schools_spatial.education_level_code",
                "app.san_jose_active_schools_spatial.neighborhood_id",
                "app.san_jose_active_schools_spatial.neighborhood_name",
                "app.san_jose_active_schools_spatial.geom",
                "core.parks.facility_id",
                "core.parks.park_name",
                "core.parks.current_status",
                "core.parks.geom",
            ),
        )

    def _average_nearest_distance(self, plan: QueryPlan) -> TemplateOutput:
        del plan
        return TemplateOutput(
            sql=self._clean("""
                WITH nearest_per_school AS (
                    SELECT
                        s.cds_code,
                        s.neighborhood_id,
                        s.neighborhood_name,
                        nearest.distance_meters
                    FROM app.san_jose_active_schools_spatial AS s
                    CROSS JOIN LATERAL (
                        SELECT
                            ST_Distance(s.geom::geography, p.geom::geography) AS distance_meters
                        FROM core.parks AS p
                        WHERE p.current_status = %s
                          AND ST_DWithin(
                              s.geom::geography,
                              p.geom::geography,
                              1609.344
                          )
                        ORDER BY ST_Distance(s.geom::geography, p.geom::geography), p.facility_id
                        LIMIT 1
                    ) AS nearest
                )
                SELECT
                    neighborhood_id,
                    neighborhood_name,
                    COUNT(DISTINCT cds_code)::integer AS active_school_count,
                    ROUND(AVG(distance_meters)::numeric, 2) AS average_nearest_park_distance_m,
                    ROUND(MIN(distance_meters)::numeric, 2) AS minimum_nearest_park_distance_m,
                    ROUND(MAX(distance_meters)::numeric, 2) AS maximum_nearest_park_distance_m
                FROM nearest_per_school
                GROUP BY neighborhood_id, neighborhood_name
                ORDER BY average_nearest_park_distance_m DESC, neighborhood_name, neighborhood_id
                LIMIT 1000
            """),
            parameters=(self._parameter(1, "park_status", "Open", "text"),),
            relations=("app.san_jose_active_schools_spatial", "core.parks"),
            source_columns=(
                "app.san_jose_active_schools_spatial.cds_code",
                "app.san_jose_active_schools_spatial.neighborhood_id",
                "app.san_jose_active_schools_spatial.neighborhood_name",
                "app.san_jose_active_schools_spatial.geom",
                "core.parks.facility_id",
                "core.parks.current_status",
                "core.parks.geom",
            ),
        )

    def _parks_with_most_schools(self, plan: QueryPlan) -> TemplateOutput:
        distance = plan.spatial_constraint.distance_meters  # type: ignore[union-attr]
        park_status = self._filter_value(plan, "core.parks.current_status")
        result_limit = plan.limit or 20
        return TemplateOutput(
            sql=self._clean("""
                SELECT
                    p.facility_id,
                    p.park_name,
                    p.park_type_code,
                    p.park_class_code,
                    COUNT(DISTINCT s.cds_code)::integer AS active_school_count_within_radius
                FROM core.parks AS p
                LEFT JOIN app.san_jose_active_schools_spatial AS s
                    ON ST_DWithin(s.geom::geography, p.geom::geography, %s)
                WHERE p.current_status = %s
                GROUP BY p.facility_id, p.park_name, p.park_type_code, p.park_class_code
                ORDER BY active_school_count_within_radius DESC, p.park_name, p.facility_id
                LIMIT %s
            """),
            parameters=(
                self._parameter(1, "distance_meters", float(distance), "double precision"),
                self._parameter(2, "park_status", str(park_status), "text"),
                self._parameter(3, "result_limit", int(result_limit), "integer"),
            ),
            relations=("app.san_jose_active_schools_spatial", "core.parks"),
            source_columns=(
                "core.parks.facility_id",
                "core.parks.park_name",
                "core.parks.park_type_code",
                "core.parks.park_class_code",
                "core.parks.current_status",
                "core.parks.geom",
                "app.san_jose_active_schools_spatial.cds_code",
                "app.san_jose_active_schools_spatial.geom",
            ),
        )

    def _neighborhoods_with_both_levels(self, plan: QueryPlan) -> TemplateOutput:
        level_values = self._filter_value(plan, "education_level_code")
        if not isinstance(level_values, list) or len(level_values) != 2:
            raise ValueError("Expected two education-level codes")
        elementary_code, high_school_code = level_values
        return TemplateOutput(
            sql=self._clean("""
                WITH level_counts AS (
                    SELECT
                        s.neighborhood_id,
                        s.neighborhood_name,
                        COUNT(DISTINCT s.cds_code) FILTER (
                            WHERE s.education_level_code = %s
                        )::integer AS elementary_school_count,
                        COUNT(DISTINCT s.cds_code) FILTER (
                            WHERE s.education_level_code = %s
                        )::integer AS high_school_count
                    FROM app.san_jose_active_schools_spatial AS s
                    GROUP BY s.neighborhood_id, s.neighborhood_name
                )
                SELECT
                    neighborhood_id,
                    neighborhood_name,
                    elementary_school_count,
                    high_school_count
                FROM level_counts
                WHERE elementary_school_count > 0
                  AND high_school_count > 0
                ORDER BY elementary_school_count DESC,
                         high_school_count DESC,
                         neighborhood_name,
                         neighborhood_id
                LIMIT 1000
            """),
            parameters=(
                self._parameter(1, "elementary_code", str(elementary_code), "text"),
                self._parameter(2, "high_school_code", str(high_school_code), "text"),
            ),
            relations=("app.san_jose_active_schools_spatial",),
            source_columns=(
                "app.san_jose_active_schools_spatial.neighborhood_id",
                "app.san_jose_active_schools_spatial.neighborhood_name",
                "app.san_jose_active_schools_spatial.cds_code",
                "app.san_jose_active_schools_spatial.education_level_code",
            ),
        )

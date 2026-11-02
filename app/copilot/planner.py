"""Rule-based Day 6 planner that produces typed plans but never SQL."""

import re

from app.copilot.schema_retrieval import SchemaRetriever
from app.models.copilot import (
    FilterOperator,
    PlanFilter,
    PlanResponse,
    PlannerIntent,
    PlanSort,
    QueryPlan,
    QueryType,
    SchemaCatalogResponse,
    SchemaContextResponse,
    SortDirection,
    SpatialConstraint,
    SpatialRelationship,
)


_WORD_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}

_WRITE_WORDS = {
    "delete", "drop", "update", "insert", "alter", "truncate", "create",
    "grant", "revoke", "vacuum", "copy",
}


class RuleBasedQueryPlanner:
    """Translate supported natural-language patterns into validated query plans.

    Day 6 intentionally stops before SQL generation or execution. The planner is
    deterministic so its behavior can be tested against the Day 4 benchmark.
    """

    def __init__(self, catalog: SchemaCatalogResponse):
        self.catalog = catalog
        self.retriever = SchemaRetriever(catalog)
        self._relation_lookup = {
            relation.qualified_name: relation for relation in catalog.relations
        }

    def plan(self, question: str, top_k: int = 6) -> PlanResponse:
        normalized = " ".join(question.strip().split())
        lower = normalized.lower()

        if self._contains_unsafe_action(lower):
            plan = self._unsupported_plan(
                question=normalized,
                intent=PlannerIntent.unsafe_request,
                warning=(
                    "The request contains a write or administrative database action. "
                    "AgenticDB-SJ Day 6 supports read-only planning only."
                ),
                confidence=1.0,
            )
            return PlanResponse(
                planner="rule_based_day6",
                plan=plan,
                schema_context=SchemaContextResponse(
                    question=normalized,
                    relations=[],
                    joins=[],
                ),
            )

        builder = self._select_builder(lower)
        if builder is None:
            plan = self._unsupported_plan(
                question=normalized,
                intent=PlannerIntent.unsupported,
                warning=(
                    "The question is outside the Day 6 supported planning patterns "
                    "or needs more domain data."
                ),
                confidence=0.35,
            )
            context = self.retriever.retrieve(normalized, top_k=top_k)
            return PlanResponse(
                planner="rule_based_day6",
                plan=plan,
                schema_context=context,
            )

        plan = builder(normalized, lower)
        context = self.retriever.retrieve(normalized, top_k=top_k)
        context = self._ensure_relations(context, plan.relations, top_k)
        return PlanResponse(
            planner="rule_based_day6",
            plan=plan,
            schema_context=context,
        )

    @staticmethod
    def _contains_unsafe_action(question: str) -> bool:
        return any(re.search(rf"\b{word}\b", question) for word in _WRITE_WORDS)

    def _select_builder(self, question: str):
        # Order matters: more specific intents must be checked first.
        if (
            "neighborhood" in question
            and "elementary" in question
            and ("high school" in question or "high-school" in question)
        ):
            return self._plan_neighborhoods_with_both_levels
        if "neighborhood" in question and "school" in question and "park" in question and (
            "at least" in question or "minimum" in question
        ):
            return self._plan_neighborhood_minimums
        if "average" in question and "nearest" in question and "park" in question:
            return self._plan_average_nearest_distance
        if "school" in question and "park" in question and (
            "no open" in question or "without" in question or "no park" in question
        ):
            return self._plan_schools_without_park
        if "park" in question and "most" in question and "school" in question:
            return self._plan_parks_with_most_schools
        if "neighborhood" in question and "park" in question and "most" in question:
            return self._plan_open_parks_per_neighborhood
        if "park" in question and "intersect" in question and "neighborhood" in question:
            return self._plan_parks_intersecting_neighborhood
        if "elementary" in question and "school" in question and "park" in question and (
            "within" in question or "near" in question
        ):
            return self._plan_elementary_schools_near_parks
        if "nearest" in question and "park" in question and "school" in question:
            return self._plan_nearest_park_per_school
        if "neighborhood" in question and "park" in question and (
            "most" in question or "how many" in question
        ):
            return self._plan_open_parks_per_neighborhood
        if "neighborhood" in question and "school" in question and (
            "how many" in question or "count" in question or "located in each" in question
        ):
            return self._plan_schools_per_neighborhood
        return None

    def _plan_schools_per_neighborhood(self, question: str, _: str) -> QueryPlan:
        return QueryPlan(
            question=question,
            intent=PlannerIntent.schools_per_neighborhood,
            query_type=QueryType.aggregate,
            confidence=0.99,
            relations=["core.neighborhoods", "app.school_neighborhoods"],
            select_fields=[
                "core.neighborhoods.enterprise_id",
                "core.neighborhoods.neighborhood_name",
                "count(distinct app.school_neighborhoods.cds_code)",
            ],
            group_by=[
                "core.neighborhoods.enterprise_id",
                "core.neighborhoods.neighborhood_name",
            ],
            sort=[PlanSort(field="active_school_count", direction=SortDirection.desc)],
            steps=[
                "Start from every neighborhood so zero-school neighborhoods remain visible.",
                "Join spatially assigned active schools by neighborhood identifier.",
                "Count distinct CDS school identifiers per neighborhood.",
            ],
            assumptions=["Active-school scope follows app.school_neighborhoods."],
        )

    def _plan_open_parks_per_neighborhood(self, question: str, _: str) -> QueryPlan:
        return QueryPlan(
            question=question,
            intent=PlannerIntent.open_parks_per_neighborhood,
            query_type=QueryType.spatial,
            confidence=0.98,
            relations=[
                "core.neighborhoods",
                "app.open_park_neighborhood_intersections",
            ],
            select_fields=[
                "core.neighborhoods.enterprise_id",
                "core.neighborhoods.neighborhood_name",
                "count(distinct app.open_park_neighborhood_intersections.facility_id)",
            ],
            group_by=[
                "core.neighborhoods.enterprise_id",
                "core.neighborhoods.neighborhood_name",
            ],
            sort=[PlanSort(field="open_park_feature_count", direction=SortDirection.desc)],
            spatial_constraint=SpatialConstraint(
                relationship=SpatialRelationship.intersects,
                left_relation="core.neighborhoods",
                right_relation="core.parks",
            ),
            steps=[
                "Start from all neighborhoods.",
                "Use the validated open-park/neighborhood intersection view.",
                "Count distinct park-source feature identifiers per neighborhood.",
            ],
            assumptions=[
                "Open park feature means a City park-dataset record with current_status = Open."
            ],
        )

    def _plan_elementary_schools_near_parks(self, question: str, lower: str) -> QueryPlan:
        distance_meters, assumption = self._extract_distance(lower)
        assumptions = [assumption] if assumption else []
        assumptions.append(
            "Elementary schools are identified by education_level_code = ELEM."
        )
        return QueryPlan(
            question=question,
            intent=PlannerIntent.elementary_schools_near_open_parks,
            query_type=QueryType.spatial,
            confidence=0.99,
            relations=["app.san_jose_active_schools_spatial", "core.parks"],
            select_fields=[
                "app.san_jose_active_schools_spatial.cds_code",
                "app.san_jose_active_schools_spatial.school_name",
                "core.parks.facility_id",
                "core.parks.park_name",
                "distance_meters",
            ],
            filters=[
                PlanFilter(
                    field="app.san_jose_active_schools_spatial.education_level_code",
                    operator=FilterOperator.eq,
                    value="ELEM",
                ),
                PlanFilter(
                    field="core.parks.current_status",
                    operator=FilterOperator.eq,
                    value="Open",
                ),
            ],
            sort=[PlanSort(field="distance_meters", direction=SortDirection.asc)],
            spatial_constraint=SpatialConstraint(
                relationship=SpatialRelationship.within_distance,
                left_relation="app.san_jose_active_schools_spatial",
                right_relation="core.parks",
                distance_meters=distance_meters,
            ),
            steps=[
                "Restrict the school view to source-coded elementary schools.",
                "Find open park-source features within the requested distance.",
                "Retain the nearest qualifying feature for each school.",
            ],
            assumptions=assumptions,
        )

    def _plan_nearest_park_per_school(self, question: str, _: str) -> QueryPlan:
        return QueryPlan(
            question=question,
            intent=PlannerIntent.nearest_open_park_per_school,
            query_type=QueryType.spatial,
            confidence=0.99,
            relations=["app.san_jose_active_schools_spatial", "core.parks"],
            select_fields=[
                "app.san_jose_active_schools_spatial.cds_code",
                "app.san_jose_active_schools_spatial.school_name",
                "core.parks.facility_id",
                "core.parks.park_name",
                "distance_meters",
            ],
            filters=[
                PlanFilter(
                    field="core.parks.current_status",
                    operator=FilterOperator.eq,
                    value="Open",
                )
            ],
            sort=[PlanSort(field="cds_code", direction=SortDirection.asc)],
            spatial_constraint=SpatialConstraint(
                relationship=SpatialRelationship.nearest,
                left_relation="app.san_jose_active_schools_spatial",
                right_relation="core.parks",
            ),
            steps=[
                "Use every in-scope active school.",
                "Calculate geography distance to open park-source features.",
                "Choose one deterministic nearest feature per school.",
            ],
            assumptions=["Distance is calculated in meters using PostGIS geography."],
        )

    def _plan_parks_intersecting_neighborhood(self, question: str, lower: str) -> QueryPlan:
        neighborhood_name = self._extract_neighborhood_name(question, lower)
        assumptions: list[str] = []
        if neighborhood_name is None:
            neighborhood_name = "UNRESOLVED"
            assumptions.append("A neighborhood name must be resolved before SQL generation.")
        return QueryPlan(
            question=question,
            intent=PlannerIntent.open_parks_intersecting_neighborhood,
            query_type=QueryType.spatial,
            confidence=0.98 if neighborhood_name != "UNRESOLVED" else 0.75,
            relations=["app.open_park_neighborhood_intersections"],
            select_fields=[
                "app.open_park_neighborhood_intersections.neighborhood_id",
                "app.open_park_neighborhood_intersections.neighborhood_name",
                "app.open_park_neighborhood_intersections.facility_id",
                "app.open_park_neighborhood_intersections.park_name",
                "app.open_park_neighborhood_intersections.intersection_area_m2",
            ],
            filters=[
                PlanFilter(
                    field="app.open_park_neighborhood_intersections.neighborhood_name",
                    operator=FilterOperator.eq,
                    value=neighborhood_name,
                )
            ],
            sort=[PlanSort(field="intersection_area_m2", direction=SortDirection.desc)],
            spatial_constraint=SpatialConstraint(
                relationship=SpatialRelationship.intersects,
                left_relation="core.parks",
                right_relation="core.neighborhoods",
            ),
            steps=[
                "Resolve the requested neighborhood to a stable neighborhood identifier.",
                "Use the validated open-feature/neighborhood intersection relation.",
                "Return intersecting feature records and intersection area.",
            ],
            assumptions=assumptions,
            requires_clarification=neighborhood_name == "UNRESOLVED",
        )

    def _plan_neighborhood_minimums(self, question: str, lower: str) -> QueryPlan:
        school_minimum = self._extract_threshold(lower, "school", default=1)
        park_minimum = self._extract_threshold(lower, "park", default=1)
        return QueryPlan(
            question=question,
            intent=PlannerIntent.neighborhoods_with_minimum_schools_and_parks,
            query_type=QueryType.hybrid,
            confidence=0.98,
            relations=[
                "core.neighborhoods",
                "app.school_neighborhoods",
                "app.open_park_neighborhood_intersections",
            ],
            select_fields=[
                "core.neighborhoods.enterprise_id",
                "core.neighborhoods.neighborhood_name",
                "active_school_count",
                "open_park_feature_count",
            ],
            filters=[
                PlanFilter(
                    field="active_school_count",
                    operator=FilterOperator.gte,
                    value=school_minimum,
                ),
                PlanFilter(
                    field="open_park_feature_count",
                    operator=FilterOperator.gte,
                    value=park_minimum,
                ),
            ],
            group_by=[
                "core.neighborhoods.enterprise_id",
                "core.neighborhoods.neighborhood_name",
            ],
            sort=[
                PlanSort(field="active_school_count", direction=SortDirection.desc),
                PlanSort(field="open_park_feature_count", direction=SortDirection.desc),
            ],
            steps=[
                "Aggregate school counts independently by neighborhood.",
                "Aggregate open park-feature counts independently by neighborhood.",
                "Join the aggregates and apply the two minimum thresholds.",
            ],
            assumptions=[
                "Independent aggregates prevent many-to-many row multiplication."
            ],
        )

    def _plan_schools_without_park(self, question: str, lower: str) -> QueryPlan:
        distance_meters, assumption = self._extract_distance(lower)
        assumptions = [assumption] if assumption else []
        return QueryPlan(
            question=question,
            intent=PlannerIntent.schools_without_nearby_open_park,
            query_type=QueryType.spatial,
            confidence=0.99,
            relations=["app.san_jose_active_schools_spatial", "core.parks"],
            select_fields=[
                "app.san_jose_active_schools_spatial.cds_code",
                "app.san_jose_active_schools_spatial.school_name",
                "nearest_open_park_id",
                "distance_meters",
            ],
            filters=[
                PlanFilter(
                    field="core.parks.current_status",
                    operator=FilterOperator.eq,
                    value="Open",
                ),
                PlanFilter(
                    field="nearby_open_park",
                    operator=FilterOperator.not_exists,
                    value=None,
                ),
            ],
            spatial_constraint=SpatialConstraint(
                relationship=SpatialRelationship.within_distance,
                left_relation="app.san_jose_active_schools_spatial",
                right_relation="core.parks",
                distance_meters=distance_meters,
                negated=True,
            ),
            steps=[
                "Evaluate each in-scope school against open park-source features.",
                "Check whether any feature exists inside the requested radius.",
                "Return only schools for which no qualifying feature exists.",
            ],
            assumptions=assumptions,
        )

    def _plan_average_nearest_distance(self, question: str, _: str) -> QueryPlan:
        return QueryPlan(
            question=question,
            intent=PlannerIntent.average_nearest_park_distance_by_neighborhood,
            query_type=QueryType.hybrid,
            confidence=0.99,
            relations=["app.san_jose_active_schools_spatial", "core.parks"],
            select_fields=[
                "app.san_jose_active_schools_spatial.neighborhood_id",
                "app.san_jose_active_schools_spatial.neighborhood_name",
                "count(cds_code)",
                "avg(nearest_distance_meters)",
                "min(nearest_distance_meters)",
                "max(nearest_distance_meters)",
            ],
            group_by=[
                "app.san_jose_active_schools_spatial.neighborhood_id",
                "app.san_jose_active_schools_spatial.neighborhood_name",
            ],
            sort=[PlanSort(field="average_nearest_park_distance_m", direction=SortDirection.asc)],
            spatial_constraint=SpatialConstraint(
                relationship=SpatialRelationship.nearest,
                left_relation="app.san_jose_active_schools_spatial",
                right_relation="core.parks",
            ),
            steps=[
                "Find one nearest open park-source feature for every in-scope school.",
                "Calculate one geography distance per school.",
                "Aggregate average, minimum, and maximum distance by neighborhood.",
            ],
            assumptions=["Only source features with current_status = Open are eligible."],
        )

    def _plan_parks_with_most_schools(self, question: str, lower: str) -> QueryPlan:
        distance_meters, assumption = self._extract_distance(lower)
        assumptions = [assumption] if assumption else []
        return QueryPlan(
            question=question,
            intent=PlannerIntent.open_parks_with_most_nearby_schools,
            query_type=QueryType.hybrid,
            confidence=0.99,
            relations=["core.parks", "app.san_jose_active_schools_spatial"],
            select_fields=[
                "core.parks.facility_id",
                "core.parks.park_name",
                "count(distinct app.san_jose_active_schools_spatial.cds_code)",
            ],
            filters=[
                PlanFilter(
                    field="core.parks.current_status",
                    operator=FilterOperator.eq,
                    value="Open",
                )
            ],
            group_by=["core.parks.facility_id", "core.parks.park_name"],
            sort=[PlanSort(field="active_school_count_within_radius", direction=SortDirection.desc)],
            spatial_constraint=SpatialConstraint(
                relationship=SpatialRelationship.within_distance,
                left_relation="core.parks",
                right_relation="app.san_jose_active_schools_spatial",
                distance_meters=distance_meters,
            ),
            limit=20,
            steps=[
                "Restrict candidate features to source status Open.",
                "Join schools inside the requested PostGIS distance radius.",
                "Count distinct schools per feature and rank descending.",
            ],
            assumptions=assumptions,
        )

    def _plan_neighborhoods_with_both_levels(self, question: str, _: str) -> QueryPlan:
        return QueryPlan(
            question=question,
            intent=PlannerIntent.neighborhoods_with_elementary_and_high_schools,
            query_type=QueryType.aggregate,
            confidence=0.99,
            relations=["app.san_jose_active_schools_spatial"],
            select_fields=[
                "app.san_jose_active_schools_spatial.neighborhood_id",
                "app.san_jose_active_schools_spatial.neighborhood_name",
                "count(*) filter (where education_level_code = ELEM)",
                "count(*) filter (where education_level_code = HS)",
            ],
            filters=[
                PlanFilter(
                    field="education_level_code",
                    operator=FilterOperator.in_,
                    value=["ELEM", "HS"],
                )
            ],
            group_by=[
                "app.san_jose_active_schools_spatial.neighborhood_id",
                "app.san_jose_active_schools_spatial.neighborhood_name",
            ],
            sort=[PlanSort(field="neighborhood_name", direction=SortDirection.asc)],
            steps=[
                "Group in-scope schools by neighborhood.",
                "Count ELEM and HS source codes independently with conditional aggregation.",
                "Keep neighborhoods where both counts are greater than zero.",
            ],
            assumptions=[
                "Elementary and high school categories use official source codes ELEM and HS."
            ],
        )

    @staticmethod
    def _unsupported_plan(
        *,
        question: str,
        intent: PlannerIntent,
        warning: str,
        confidence: float,
    ) -> QueryPlan:
        return QueryPlan(
            question=question,
            intent=intent,
            query_type=QueryType.unsupported,
            confidence=confidence,
            relations=[],
            select_fields=[],
            steps=["Do not generate or execute SQL for this request."],
            warnings=[warning],
            requires_clarification=intent == PlannerIntent.unsupported,
        )

    @staticmethod
    def _extract_distance(question: str) -> tuple[float, str | None]:
        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(miles?|mi|kilometers?|kilometres?|km)\b",
            question,
        )
        if not match:
            return 1609.344, "No distance was stated; the Day 4 default of one mile is used."
        value = float(match.group(1))
        unit = match.group(2)
        if unit in {"mile", "miles", "mi"}:
            return value * 1609.344, None
        return value * 1000.0, None

    @staticmethod
    def _extract_threshold(question: str, noun: str, default: int) -> int:
        pattern = rf"(?:at least|minimum(?: of)?)\s+(\d+|[a-z]+)\s+(?:active\s+|open\s+)?{noun}s?"
        match = re.search(pattern, question)
        if not match:
            # The second threshold in phrases like "three schools and two parks"
            # may not repeat "at least".
            match = re.search(rf"\b(\d+|[a-z]+)\s+(?:active\s+|open\s+)?{noun}s?\b", question)
        if not match:
            return default
        raw = match.group(1)
        return int(raw) if raw.isdigit() else _WORD_NUMBERS.get(raw, default)

    @staticmethod
    def _extract_neighborhood_name(question: str, lower: str) -> str | None:
        match = re.search(
            r"intersect(?:ing)?\s+(?:the\s+)?(.+?)\s+neighborhood\b",
            lower,
        )
        if match:
            phrase = match.group(1).strip(" ?.,")
            # Preserve capitalization from common title formatting for plan output.
            return " ".join(word.capitalize() for word in phrase.split())
        # Handle "in the Almaden Lake neighborhood" wording.
        match = re.search(r"in\s+(?:the\s+)?(.+?)\s+neighborhood\b", lower)
        if match:
            phrase = match.group(1).strip(" ?.,")
            return " ".join(word.capitalize() for word in phrase.split())
        del question
        return None

    def _ensure_relations(
        self,
        context: SchemaContextResponse,
        required_relations: list[str],
        top_k: int,
    ) -> SchemaContextResponse:
        from app.models.copilot import RetrievedRelation

        existing = {
            item.relation.qualified_name: item for item in context.relations
        }
        required_items: list[RetrievedRelation] = []

        for required in required_relations:
            item = existing.get(required)
            if item is not None:
                required_items.append(
                    RetrievedRelation(
                        relation=item.relation,
                        relevance_score=max(item.relevance_score, 1000.0),
                        matched_terms=sorted(
                            set(item.matched_terms).union({"required_by_plan"})
                        ),
                    )
                )
                continue

            relation = self._relation_lookup.get(required)
            if relation is not None and relation.available:
                required_items.append(
                    RetrievedRelation(
                        relation=relation,
                        relevance_score=1000.0,
                        matched_terms=["required_by_plan"],
                    )
                )

        required_names = {
            item.relation.qualified_name for item in required_items
        }
        extras = [
            item
            for item in context.relations
            if item.relation.qualified_name not in required_names
        ]
        extras.sort(
            key=lambda item: (
                -item.relevance_score,
                item.relation.qualified_name,
            )
        )

        # Required relations always survive, even when top_k is smaller.
        extra_slots = max(0, top_k - len(required_items))
        relations = required_items + extras[:extra_slots]
        names = {item.relation.qualified_name for item in relations}
        joins = [
            join
            for join in self.catalog.joins
            if join.left_relation in names and join.right_relation in names
        ]
        return SchemaContextResponse(
            question=context.question,
            relations=relations,
            joins=joins,
        )

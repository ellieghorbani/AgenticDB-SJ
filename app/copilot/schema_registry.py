"""Curated schema allowlist and semantic metadata for the copilot.

The registry intentionally exposes only relations and columns that are useful to
supported public-data questions. It is not a dump of the whole database.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ColumnDefinition:
    name: str
    data_type: str
    nullable: bool
    description: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RelationDefinition:
    qualified_name: str
    expected_relation_type: str
    description: str
    aliases: tuple[str, ...]
    primary_key_columns: tuple[str, ...]
    geometry_column: str | None
    columns: tuple[ColumnDefinition, ...]

    @property
    def schema_name(self) -> str:
        return self.qualified_name.split(".", maxsplit=1)[0]

    @property
    def relation_name(self) -> str:
        return self.qualified_name.split(".", maxsplit=1)[1]


@dataclass(frozen=True, slots=True)
class JoinDefinition:
    left_relation: str
    right_relation: str
    join_condition: str
    relationship: str
    description: str


RELATIONS: tuple[RelationDefinition, ...] = (
    RelationDefinition(
        qualified_name="core.neighborhoods",
        expected_relation_type="BASE TABLE",
        description=(
            "Official San Jose neighborhood polygons with stable identifiers, "
            "names, geometry-repair provenance, and source lineage."
        ),
        aliases=("neighborhood", "neighborhoods", "area", "areas", "district area"),
        primary_key_columns=("enterprise_id",),
        geometry_column="geom",
        columns=(
            ColumnDefinition(
                "enterprise_id", "text", False,
                "Stable source identifier for a neighborhood polygon.",
                ("id", "neighborhood"),
            ),
            ColumnDefinition(
                "neighborhood_name", "text", False,
                "Human-readable neighborhood name; names are not guaranteed unique.",
                ("name", "neighborhood"),
            ),
            ColumnDefinition(
                "geom_repaired", "boolean", False,
                "Whether the source geometry required deterministic repair.",
                ("quality", "geometry"),
            ),
            ColumnDefinition(
                "geom", "geometry", False,
                "MultiPolygon geometry in SRID 4326.",
                ("polygon", "spatial", "boundary", "contains", "intersects"),
            ),
            ColumnDefinition(
                "source_id", "bigint", False,
                "Foreign key to the source registry.",
                ("provenance", "source"),
            ),
        ),
    ),
    RelationDefinition(
        qualified_name="core.parks",
        expected_relation_type="BASE TABLE",
        description=(
            "City of San Jose park-dataset features, including source-coded parks, "
            "trails, recreation facilities, libraries, and related polygons."
        ),
        aliases=(
            "park", "parks", "open park", "open parks", "park feature",
            "park features", "recreation feature", "trail",
        ),
        primary_key_columns=("facility_id",),
        geometry_column="geom",
        columns=(
            ColumnDefinition(
                "facility_id", "text", False,
                "Stable identifier for a park-dataset feature.",
                ("id", "park"),
            ),
            ColumnDefinition(
                "park_name", "text", False,
                "Source-provided feature name.",
                ("name", "park"),
            ),
            ColumnDefinition(
                "park_type_code", "text", False,
                "Source park-type code.",
                ("category", "type", "park"),
            ),
            ColumnDefinition(
                "park_class_code", "text", False,
                "Source park-class code.",
                ("category", "class", "park"),
            ),
            ColumnDefinition(
                "subclass_code", "text", True,
                "Optional source subclass code; one real record is unspecified.",
                ("category", "subclass", "park"),
            ),
            ColumnDefinition(
                "current_status", "text", False,
                "Source operational status such as Open, Seasonal, or Future.",
                ("status", "open", "closed"),
            ),
            ColumnDefinition(
                "all_acres", "numeric", True,
                "Source-reported total acreage when available.",
                ("area", "acres", "size"),
            ),
            ColumnDefinition(
                "planning_area", "text", True,
                "Source planning-area label.",
                ("planning", "area"),
            ),
            ColumnDefinition(
                "geom", "geometry", False,
                "MultiPolygon geometry in SRID 4326.",
                ("polygon", "spatial", "distance", "near", "intersects"),
            ),
            ColumnDefinition(
                "source_id", "bigint", False,
                "Foreign key to the source registry.",
                ("provenance", "source"),
            ),
        ),
    ),
    RelationDefinition(
        qualified_name="core.schools",
        expected_relation_type="BASE TABLE",
        description=(
            "Active California public-school records with official CDS identifiers, "
            "district and education-level attributes, and point geometry."
        ),
        aliases=(
            "school", "schools", "public school", "public schools",
            "elementary school", "high school", "district",
        ),
        primary_key_columns=("cds_code",),
        geometry_column="geom",
        columns=(
            ColumnDefinition(
                "cds_code", "character", False,
                "Official 14-character California school identifier.",
                ("id", "school", "cds"),
            ),
            ColumnDefinition(
                "status_type", "text", False,
                "Official source status; loaded records are Active.",
                ("status", "active"),
            ),
            ColumnDefinition(
                "district_name", "text", False,
                "Public-school district name.",
                ("district", "school"),
            ),
            ColumnDefinition(
                "school_name", "text", True,
                "Official school name.",
                ("name", "school"),
            ),
            ColumnDefinition(
                "city", "text", True,
                "Source mailing-city label, not the spatial scope definition.",
                ("city", "location"),
            ),
            ColumnDefinition(
                "education_level_code", "text", True,
                "Source-coded education level, including ELEM and HS.",
                ("elementary", "high school", "level", "grade"),
            ),
            ColumnDefinition(
                "education_level_name", "text", True,
                "Human-readable education-level label.",
                ("elementary", "high school", "level", "grade"),
            ),
            ColumnDefinition(
                "grades_served", "text", True,
                "Source description of grades served.",
                ("grade", "grades", "school"),
            ),
            ColumnDefinition(
                "geom", "geometry", True,
                "Point geometry in SRID 4326.",
                ("point", "spatial", "distance", "near", "within"),
            ),
            ColumnDefinition(
                "source_id", "bigint", False,
                "Foreign key to the source registry.",
                ("provenance", "source"),
            ),
        ),
    ),
    RelationDefinition(
        qualified_name="app.school_neighborhoods",
        expected_relation_type="VIEW",
        description=(
            "Spatial relationship assigning each in-scope active school to the "
            "San Jose neighborhood polygon that contains its point."
        ),
        aliases=(
            "school neighborhood", "schools by neighborhood",
            "schools per neighborhood", "school containment",
        ),
        primary_key_columns=("cds_code", "neighborhood_id"),
        geometry_column=None,
        columns=(
            ColumnDefinition("cds_code", "character", False, "Official school identifier.", ("school", "id")),
            ColumnDefinition("school_name", "text", False, "Official school name.", ("school", "name")),
            ColumnDefinition("district_name", "text", False, "School district name.", ("district",)),
            ColumnDefinition("source_city", "text", True, "Original mailing-city value.", ("city",)),
            ColumnDefinition("neighborhood_id", "text", False, "Containing neighborhood identifier.", ("neighborhood", "id")),
            ColumnDefinition("neighborhood_name", "text", False, "Containing neighborhood name.", ("neighborhood", "name")),
        ),
    ),
    RelationDefinition(
        qualified_name="app.san_jose_active_schools_spatial",
        expected_relation_type="VIEW",
        description=(
            "Active schools spatially contained by the supplied San Jose neighborhood "
            "polygons, with neighborhood identifiers and school geometry."
        ),
        aliases=(
            "San Jose schools", "active schools", "schools in scope",
            "in-scope schools", "school points",
        ),
        primary_key_columns=("cds_code",),
        geometry_column="geom",
        columns=(
            ColumnDefinition("cds_code", "character", False, "Official school identifier.", ("school", "id")),
            ColumnDefinition("school_name", "text", False, "Official school name.", ("school", "name")),
            ColumnDefinition("district_name", "text", False, "School district name.", ("district",)),
            ColumnDefinition("city", "text", True, "Original mailing-city label.", ("city",)),
            ColumnDefinition("education_level_code", "text", True, "Source education-level code.", ("elementary", "high school", "level")),
            ColumnDefinition("education_level_name", "text", True, "Education-level label.", ("elementary", "high school", "level")),
            ColumnDefinition("geom", "geometry", False, "School point geometry in SRID 4326.", ("point", "spatial", "distance", "near")),
            ColumnDefinition("neighborhood_id", "text", False, "Containing neighborhood identifier.", ("neighborhood", "id")),
            ColumnDefinition("neighborhood_name", "text", False, "Containing neighborhood name.", ("neighborhood", "name")),
        ),
    ),
    RelationDefinition(
        qualified_name="app.open_park_neighborhood_intersections",
        expected_relation_type="VIEW",
        description=(
            "Precomputed relationships between open park-dataset polygons and the "
            "neighborhood polygons they spatially intersect."
        ),
        aliases=(
            "open parks by neighborhood", "park neighborhood intersections",
            "parks per neighborhood", "open park intersections",
        ),
        primary_key_columns=("facility_id", "neighborhood_id"),
        geometry_column=None,
        columns=(
            ColumnDefinition("facility_id", "text", False, "Park-feature identifier.", ("park", "id")),
            ColumnDefinition("park_name", "text", False, "Park-feature name.", ("park", "name")),
            ColumnDefinition("park_type_code", "text", False, "Source park-type code.", ("park", "type")),
            ColumnDefinition("park_class_code", "text", False, "Source park-class code.", ("park", "class")),
            ColumnDefinition("neighborhood_id", "text", False, "Intersected neighborhood identifier.", ("neighborhood", "id")),
            ColumnDefinition("neighborhood_name", "text", False, "Intersected neighborhood name.", ("neighborhood", "name")),
            ColumnDefinition("intersection_area_m2", "double precision", True, "Intersection area in square meters.", ("area", "intersection", "spatial")),
        ),
    ),
)


JOINS: tuple[JoinDefinition, ...] = (
    JoinDefinition(
        "core.neighborhoods",
        "app.school_neighborhoods",
        "core.neighborhoods.enterprise_id = app.school_neighborhoods.neighborhood_id",
        "one_to_many",
        "Connect each neighborhood to the active schools spatially assigned to it.",
    ),
    JoinDefinition(
        "core.neighborhoods",
        "app.open_park_neighborhood_intersections",
        "core.neighborhoods.enterprise_id = app.open_park_neighborhood_intersections.neighborhood_id",
        "one_to_many",
        "Connect each neighborhood to open park-dataset features that intersect it.",
    ),
    JoinDefinition(
        "core.schools",
        "app.school_neighborhoods",
        "core.schools.cds_code = app.school_neighborhoods.cds_code",
        "one_to_one_in_scope",
        "Attach the containing neighborhood to an active school record.",
    ),
    JoinDefinition(
        "core.schools",
        "app.san_jose_active_schools_spatial",
        "core.schools.cds_code = app.san_jose_active_schools_spatial.cds_code",
        "one_to_one_in_scope",
        "Restrict statewide active schools to the spatial San Jose scope.",
    ),
)


RELATION_BY_NAME = {relation.qualified_name: relation for relation in RELATIONS}

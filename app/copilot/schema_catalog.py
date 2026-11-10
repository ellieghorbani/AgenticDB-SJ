"""Database-backed schema catalog limited by the curated allowlist."""

from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from psycopg import Connection

from app.copilot.schema_registry import JOINS, RELATIONS
from app.models.copilot import (
    SchemaCatalogResponse,
    SchemaColumn,
    SchemaJoin,
    SchemaRelation,
)


_INTROSPECTION_SQL = """
SELECT
    t.table_schema,
    t.table_name,
    t.table_type,
    c.column_name,
    CASE
        WHEN c.data_type = 'USER-DEFINED' THEN c.udt_name
        ELSE c.data_type
    END AS data_type,
    (c.is_nullable = 'YES') AS nullable
FROM information_schema.tables AS t
JOIN information_schema.columns AS c
  ON c.table_schema = t.table_schema
 AND c.table_name = t.table_name
WHERE (t.table_schema || '.' || t.table_name) = ANY(%s)
ORDER BY
    t.table_schema,
    t.table_name,
    c.ordinal_position;
"""


class SchemaCatalogService:
    """Read actual relation metadata and merge it with semantic descriptions."""

    def __init__(self, connection: "Connection"):
        self.connection = connection

    def catalog(self) -> SchemaCatalogResponse:
        allowed_names = [definition.qualified_name for definition in RELATIONS]
        with self.connection.cursor() as cursor:
            cursor.execute(_INTROSPECTION_SQL, (allowed_names,))
            rows = [dict(row) for row in cursor.fetchall()]

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            qualified_name = f"{row['table_schema']}.{row['table_name']}"
            grouped[qualified_name].append(row)

        relations: list[SchemaRelation] = []
        for definition in RELATIONS:
            actual_rows = grouped.get(definition.qualified_name, [])
            actual_by_column = {row["column_name"]: row for row in actual_rows}
            actual_relation_type = (
                actual_rows[0]["table_type"]
                if actual_rows
                else definition.expected_relation_type
            )

            columns: list[SchemaColumn] = []
            for column in definition.columns:
                actual = actual_by_column.get(column.name)
                if actual is None and actual_rows:
                    # The relation exists but this allowlisted column does not. Do not
                    # expose a column that is absent from the real database.
                    continue
                columns.append(
                    SchemaColumn(
                        name=column.name,
                        data_type=(actual["data_type"] if actual else column.data_type),
                        nullable=(actual["nullable"] if actual else column.nullable),
                        description=column.description,
                        semantic_tags=list(column.tags),
                    )
                )

            relations.append(
                SchemaRelation(
                    qualified_name=definition.qualified_name,
                    schema_name=definition.schema_name,
                    relation_name=definition.relation_name,
                    relation_type=actual_relation_type,
                    available=bool(actual_rows),
                    description=definition.description,
                    aliases=list(definition.aliases),
                    primary_key_columns=list(definition.primary_key_columns),
                    geometry_column=definition.geometry_column,
                    columns=columns,
                )
            )

        return SchemaCatalogResponse(
            generated_from="curated_allowlist+information_schema",
            relation_count=sum(relation.available for relation in relations),
            relations=relations,
            joins=[
                SchemaJoin(
                    left_relation=join.left_relation,
                    right_relation=join.right_relation,
                    join_condition=join.join_condition,
                    relationship=join.relationship,
                    description=join.description,
                )
                for join in JOINS
            ],
        )


def build_static_catalog() -> SchemaCatalogResponse:
    """Build a database-independent catalog for unit tests and offline validation."""

    return SchemaCatalogResponse(
        generated_from="static_registry",
        relation_count=len(RELATIONS),
        relations=[
            SchemaRelation(
                qualified_name=definition.qualified_name,
                schema_name=definition.schema_name,
                relation_name=definition.relation_name,
                relation_type=definition.expected_relation_type,
                available=True,
                description=definition.description,
                aliases=list(definition.aliases),
                primary_key_columns=list(definition.primary_key_columns),
                geometry_column=definition.geometry_column,
                columns=[
                    SchemaColumn(
                        name=column.name,
                        data_type=column.data_type,
                        nullable=column.nullable,
                        description=column.description,
                        semantic_tags=list(column.tags),
                    )
                    for column in definition.columns
                ],
            )
            for definition in RELATIONS
        ],
        joins=[
            SchemaJoin(
                left_relation=join.left_relation,
                right_relation=join.right_relation,
                join_condition=join.join_condition,
                relationship=join.relationship,
                description=join.description,
            )
            for join in JOINS
        ],
    )

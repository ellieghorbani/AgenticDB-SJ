"""Parameterized relational and spatial queries for the Day 5 API."""

from typing import Any

from psycopg import Connection

from app.core.errors import ResourceNotFoundError


_NEIGHBORHOOD_METRICS_CTE = """
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
),
metrics AS (
    SELECT
        n.enterprise_id AS neighborhood_id,
        n.neighborhood_name,
        sc.active_school_count,
        pc.open_park_feature_count
    FROM core.neighborhoods AS n
    JOIN school_counts AS sc
        ON sc.neighborhood_id = n.enterprise_id
    JOIN park_counts AS pc
        ON pc.neighborhood_id = n.enterprise_id
)
"""


class QueryService:
    """Read-only database operations used by the HTTP route layer."""

    def __init__(self, connection: Connection):
        self.connection = connection

    def _fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
        return dict(row) if row is not None else None

    def _fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def readiness(self) -> dict[str, Any]:
        row = self._fetch_one(
            """
            SELECT
                current_database() AS database,
                current_user AS database_user,
                PostGIS_Version() AS postgis_version
            """
        )
        assert row is not None
        return {"status": "ready", **row}

    def snapshot(self) -> dict[str, Any]:
        row = self._fetch_one(
            """
            SELECT
                (SELECT COUNT(*)::integer FROM core.neighborhoods) AS neighborhoods,
                (SELECT COUNT(*)::integer FROM core.parks) AS parks,
                (SELECT COUNT(*)::integer FROM core.schools) AS active_schools,
                (
                    SELECT COUNT(*)::integer
                    FROM app.san_jose_active_schools_spatial
                ) AS schools_in_scope,
                (
                    SELECT COUNT(*)::integer
                    FROM core.parks
                    WHERE current_status = 'Open'
                ) AS open_park_features,
                (
                    SELECT COUNT(*)::integer
                    FROM metadata.source_registry
                ) AS registered_sources,
                (
                    SELECT COUNT(*)::integer
                    FROM metadata.ingestion_runs
                    WHERE status = 'succeeded'
                ) AS successful_ingestion_runs
            """
        )
        assert row is not None
        return row

    def list_neighborhoods(
        self,
        *,
        min_schools: int,
        min_open_park_features: int,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = """
        WHERE active_school_count >= %s
          AND open_park_feature_count >= %s
        """
        params = (min_schools, min_open_park_features)

        total_row = self._fetch_one(
            _NEIGHBORHOOD_METRICS_CTE
            + """
            SELECT COUNT(*)::integer AS total
            FROM metrics
            """
            + filters,
            params,
        )
        assert total_row is not None

        items = self._fetch_all(
            _NEIGHBORHOOD_METRICS_CTE
            + """
            SELECT
                neighborhood_id,
                neighborhood_name,
                active_school_count,
                open_park_feature_count
            FROM metrics
            """
            + filters
            + """
            ORDER BY
                active_school_count DESC,
                open_park_feature_count DESC,
                neighborhood_name,
                neighborhood_id
            LIMIT %s OFFSET %s
            """,
            params + (limit, offset),
        )
        return items, int(total_row["total"])

    def neighborhood_summary(self, neighborhood_id: str) -> dict[str, Any]:
        row = self._fetch_one(
            """
            SELECT
                n.enterprise_id AS neighborhood_id,
                n.neighborhood_name,
                (
                    SELECT COUNT(DISTINCT sn.cds_code)::integer
                    FROM app.school_neighborhoods AS sn
                    WHERE sn.neighborhood_id = n.enterprise_id
                ) AS active_school_count,
                (
                    SELECT COUNT(DISTINCT op.facility_id)::integer
                    FROM app.open_park_neighborhood_intersections AS op
                    WHERE op.neighborhood_id = n.enterprise_id
                ) AS open_park_feature_count,
                ROUND(
                    (ST_Area(n.geom::geography) / 1000000.0)::numeric,
                    4
                ) AS area_sq_km
            FROM core.neighborhoods AS n
            WHERE n.enterprise_id = %s
            """,
            (neighborhood_id,),
        )
        if row is None:
            raise ResourceNotFoundError(
                f"Neighborhood '{neighborhood_id}' was not found."
            )
        return row

    def schools_near_open_parks(
        self,
        *,
        distance_miles: float,
        education_level_code: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        distance_meters = distance_miles * 1609.344
        level = education_level_code.upper() if education_level_code else None

        rows = self._fetch_all(
            """
            WITH matches AS (
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
                    ROUND(
                        (nearest.distance_meters / 1609.344)::numeric,
                        4
                    ) AS distance_miles
                FROM app.san_jose_active_schools_spatial AS s
                CROSS JOIN LATERAL (
                    SELECT
                        p.facility_id,
                        p.park_name,
                        p.park_type_code,
                        p.park_class_code,
                        ST_Distance(
                            s.geom::geography,
                            p.geom::geography
                        ) AS distance_meters
                    FROM core.parks AS p
                    WHERE p.current_status = 'Open'
                      AND ST_DWithin(
                          s.geom::geography,
                          p.geom::geography,
                          %s
                     )
                   ORDER BY
                      ST_Distance(s.geom::geography, p.geom::geography),
                      p.facility_id
                  LIMIT 1
                  ) AS nearest
                  WHERE (%s::text IS NULL OR s.education_level_code = %s::text)
            )
            SELECT
                matches.*,
                COUNT(*) OVER ()::integer AS total_count
            FROM matches
            ORDER BY
                distance_meters,
                school_name,
                cds_code
            LIMIT %s OFFSET %s
            """,
            (distance_meters, level, level, limit, offset),
        )

        total = int(rows[0]["total_count"]) if rows else 0
        for row in rows:
            row.pop("total_count", None)
        return rows, total

    def park_nearby_schools(
        self,
        *,
        facility_id: str,
        distance_miles: float,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        park = self._fetch_one(
            """
            SELECT
                facility_id,
                park_name,
                park_type_code,
                park_class_code,
                current_status
            FROM core.parks
            WHERE facility_id = %s
            """,
            (facility_id,),
        )
        if park is None:
            raise ResourceNotFoundError(f"Park '{facility_id}' was not found.")

        distance_meters = distance_miles * 1609.344
        rows = self._fetch_all(
            """
            WITH matches AS (
                SELECT
                    s.cds_code,
                    s.school_name,
                    s.district_name,
                    s.education_level_code,
                    s.education_level_name,
                    s.neighborhood_id,
                    s.neighborhood_name,
                    ROUND(
                        ST_Distance(
                            s.geom::geography,
                            p.geom::geography
                        )::numeric,
                        2
                    ) AS distance_meters,
                    ROUND(
                        (
                            ST_Distance(
                                s.geom::geography,
                                p.geom::geography
                            ) / 1609.344
                        )::numeric,
                        4
                    ) AS distance_miles
                FROM core.parks AS p
                JOIN app.san_jose_active_schools_spatial AS s
                    ON ST_DWithin(
                        s.geom::geography,
                        p.geom::geography,
                        %s
                    )
                WHERE p.facility_id = %s
            )
            SELECT
                matches.*,
                COUNT(*) OVER ()::integer AS total_count
            FROM matches
            ORDER BY
                distance_meters,
                school_name,
                cds_code
            LIMIT %s OFFSET %s
            """,
            (distance_meters, facility_id, limit, offset),
        )

        total = int(rows[0]["total_count"]) if rows else 0
        for row in rows:
            row.pop("total_count", None)

        return {
            "park": park,
            "distance_miles": distance_miles,
            "items": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

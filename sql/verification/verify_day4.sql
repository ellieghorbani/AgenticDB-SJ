\pset pager off
\echo 'Day 4 fixed-snapshot benchmark checks'

WITH
q01 AS (
    SELECT n.enterprise_id, COUNT(DISTINCT sn.cds_code) AS value
    FROM core.neighborhoods n
    LEFT JOIN app.school_neighborhoods sn ON sn.neighborhood_id = n.enterprise_id
    GROUP BY n.enterprise_id
),
q02 AS (
    SELECT n.enterprise_id, COUNT(DISTINCT op.facility_id) AS value
    FROM core.neighborhoods n
    LEFT JOIN app.open_park_neighborhood_intersections op
      ON op.neighborhood_id = n.enterprise_id
    GROUP BY n.enterprise_id
),
nearest AS (
    SELECT
        s.cds_code,
        s.education_level_code,
        s.neighborhood_id,
        nearest.distance_meters
    FROM app.san_jose_active_schools_spatial s
    CROSS JOIN LATERAL (
        SELECT ST_Distance(s.geom::geography, p.geom::geography) AS distance_meters
        FROM core.parks p
        WHERE p.current_status = 'Open'
        ORDER BY ST_Distance(s.geom::geography, p.geom::geography), p.facility_id
        LIMIT 1
    ) nearest
),
q06 AS (
    SELECT n.enterprise_id
    FROM core.neighborhoods n
    JOIN q01 s ON s.enterprise_id = n.enterprise_id
    JOIN q02 p ON p.enterprise_id = n.enterprise_id
    WHERE s.value >= 3 AND p.value >= 2
),
q10 AS (
    SELECT s.neighborhood_id
    FROM app.san_jose_active_schools_spatial s
    GROUP BY s.neighborhood_id
    HAVING COUNT(DISTINCT s.cds_code) FILTER (WHERE s.education_level_code = 'ELEM') > 0
       AND COUNT(DISTINCT s.cds_code) FILTER (WHERE s.education_level_code = 'HS') > 0
),
metrics AS (
    SELECT 'q01_rows' AS metric, COUNT(*)::bigint AS actual, 297::bigint AS expected FROM q01
    UNION ALL SELECT 'q01_school_count_sum', SUM(value), 220 FROM q01
    UNION ALL SELECT 'q02_rows', COUNT(*), 297 FROM q02
    UNION ALL SELECT 'q02_intersection_count_sum', SUM(value), 609 FROM q02
    UNION ALL SELECT 'q03_rows', COUNT(*), 131 FROM nearest WHERE education_level_code = 'ELEM' AND distance_meters <= 1609.344
    UNION ALL SELECT 'q04_rows', COUNT(*), 220 FROM nearest
    UNION ALL SELECT 'q05_rows', COUNT(*), 6 FROM app.open_park_neighborhood_intersections WHERE neighborhood_id = 'REF-NEIG-0000000194'
    UNION ALL SELECT 'q06_rows', COUNT(*), 15 FROM q06
    UNION ALL SELECT 'q07_rows', COUNT(*), 0 FROM nearest WHERE distance_meters > 1609.344
    UNION ALL SELECT 'q08_rows', COUNT(DISTINCT neighborhood_id), 134 FROM nearest
    UNION ALL SELECT 'q10_rows', COUNT(*), 18 FROM q10
)
SELECT
    metric,
    actual,
    expected,
    actual = expected AS passed
FROM metrics
ORDER BY metric;

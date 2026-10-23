-- Q07: Which active schools have no open park feature within one mile?
-- A zero-row answer is valid and is intentionally retained as an agent test case.
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
CROSS JOIN LATERAL (
    SELECT
        p.facility_id,
        p.park_name,
        ST_Distance(
            s.geom::geography,
            p.geom::geography
        ) AS distance_meters
    FROM core.parks AS p
    WHERE p.current_status = 'Open'
    ORDER BY
        ST_Distance(s.geom::geography, p.geom::geography),
        p.facility_id
    LIMIT 1
) AS nearest
WHERE nearest.distance_meters > 1609.344
ORDER BY
    nearest.distance_meters DESC,
    s.school_name,
    s.cds_code;

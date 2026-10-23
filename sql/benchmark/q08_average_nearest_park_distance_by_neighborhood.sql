-- Q08: What is the average distance from active schools to their nearest open park
-- feature, grouped by neighborhood?
WITH nearest_per_school AS (
    SELECT
        s.cds_code,
        s.neighborhood_id,
        s.neighborhood_name,
        nearest.distance_meters
    FROM app.san_jose_active_schools_spatial AS s
    CROSS JOIN LATERAL (
        SELECT
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
)
SELECT
    neighborhood_id,
    neighborhood_name,
    COUNT(DISTINCT cds_code)::integer AS active_school_count,
    ROUND(AVG(distance_meters)::numeric, 2) AS average_nearest_park_distance_m,
    ROUND(MIN(distance_meters)::numeric, 2) AS minimum_nearest_park_distance_m,
    ROUND(MAX(distance_meters)::numeric, 2) AS maximum_nearest_park_distance_m
FROM nearest_per_school
GROUP BY
    neighborhood_id,
    neighborhood_name
ORDER BY
    average_nearest_park_distance_m DESC,
    neighborhood_name,
    neighborhood_id;

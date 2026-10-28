-- Q03: Which active elementary schools are within one mile of an open park feature?
-- One deterministic row is returned per school: its nearest open feature.
-- Geography casts make distance units meters; 1 mile = 1609.344 meters.
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
WHERE s.education_level_code = 'ELEM'
  AND nearest.distance_meters <= 1609.344
ORDER BY
    nearest.distance_meters,
    s.school_name,
    s.cds_code;

-- Q09: Which open park features have the largest number of active schools within one mile?
-- The output is deliberately limited to the top 20 and uses distinct school IDs.
SELECT
    p.facility_id,
    p.park_name,
    p.park_type_code,
    p.park_class_code,
    COUNT(DISTINCT s.cds_code)::integer AS active_school_count_within_one_mile
FROM core.parks AS p
LEFT JOIN app.san_jose_active_schools_spatial AS s
    ON ST_DWithin(
        s.geom::geography,
        p.geom::geography,
        1609.344
    )
WHERE p.current_status = 'Open'
GROUP BY
    p.facility_id,
    p.park_name,
    p.park_type_code,
    p.park_class_code
ORDER BY
    active_school_count_within_one_mile DESC,
    p.park_name,
    p.facility_id
LIMIT 20;

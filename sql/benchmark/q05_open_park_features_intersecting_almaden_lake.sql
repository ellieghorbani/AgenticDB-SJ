-- Q05: Which open park features intersect the selected Almaden Lake neighborhood?
-- The benchmark fixes the target by unique source identifier to avoid ambiguous names.
SELECT
    op.neighborhood_id,
    op.neighborhood_name,
    op.facility_id,
    op.park_name,
    op.park_type_code,
    op.park_class_code,
    ROUND(op.intersection_area_m2::numeric, 2) AS intersection_area_m2
FROM app.open_park_neighborhood_intersections AS op
WHERE op.neighborhood_id = 'REF-NEIG-0000000194'
ORDER BY
    op.intersection_area_m2 DESC,
    op.park_name,
    op.facility_id;

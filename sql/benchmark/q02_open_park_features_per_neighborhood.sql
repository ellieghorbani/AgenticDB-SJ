-- Q02: Which neighborhoods contain/intersect the most open park-dataset features?
-- "Open park feature" means any core.parks source record with current_status = 'Open'.
-- This deliberately includes trails, libraries, school properties, and other source types.
SELECT
    n.enterprise_id AS neighborhood_id,
    n.neighborhood_name,
    COUNT(DISTINCT op.facility_id)::integer AS open_park_feature_count
FROM core.neighborhoods AS n
LEFT JOIN app.open_park_neighborhood_intersections AS op
    ON op.neighborhood_id = n.enterprise_id
GROUP BY
    n.enterprise_id,
    n.neighborhood_name
ORDER BY
    open_park_feature_count DESC,
    n.neighborhood_name,
    n.enterprise_id;

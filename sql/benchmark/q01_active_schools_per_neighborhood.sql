-- Q01: How many active public schools are located in each neighborhood?
-- Scope: all 297 neighborhood polygons; neighborhoods with zero schools are retained.
SELECT
    n.enterprise_id AS neighborhood_id,
    n.neighborhood_name,
    COUNT(DISTINCT sn.cds_code)::integer AS active_school_count
FROM core.neighborhoods AS n
LEFT JOIN app.school_neighborhoods AS sn
    ON sn.neighborhood_id = n.enterprise_id
GROUP BY
    n.enterprise_id,
    n.neighborhood_name
ORDER BY
    active_school_count DESC,
    n.neighborhood_name,
    n.enterprise_id;

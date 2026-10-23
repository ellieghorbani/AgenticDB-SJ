-- Q06: Which neighborhoods have at least three active schools and two open park features?
-- Counts are calculated independently before joining to avoid a many-to-many overcount.
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
)
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
WHERE sc.active_school_count >= 3
  AND pc.open_park_feature_count >= 2
ORDER BY
    sc.active_school_count DESC,
    pc.open_park_feature_count DESC,
    n.neighborhood_name,
    n.enterprise_id;

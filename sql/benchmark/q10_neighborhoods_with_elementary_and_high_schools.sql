-- Q10: Which neighborhoods contain both active elementary and active high-school records?
-- The benchmark uses the source categories ELEM and HS exactly; combination schools are
-- not silently counted as both categories.
SELECT
    s.neighborhood_id,
    s.neighborhood_name,
    COUNT(DISTINCT s.cds_code) FILTER (
        WHERE s.education_level_code = 'ELEM'
    )::integer AS elementary_school_count,
    COUNT(DISTINCT s.cds_code) FILTER (
        WHERE s.education_level_code = 'HS'
    )::integer AS high_school_count
FROM app.san_jose_active_schools_spatial AS s
GROUP BY
    s.neighborhood_id,
    s.neighborhood_name
HAVING COUNT(DISTINCT s.cds_code) FILTER (
           WHERE s.education_level_code = 'ELEM'
       ) > 0
   AND COUNT(DISTINCT s.cds_code) FILTER (
           WHERE s.education_level_code = 'HS'
       ) > 0
ORDER BY
    elementary_school_count DESC,
    high_school_count DESC,
    s.neighborhood_name,
    s.neighborhood_id;

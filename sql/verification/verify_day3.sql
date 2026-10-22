\pset pager off

SELECT
    'neighborhoods' AS dataset,
    COUNT(*) AS row_count
FROM core.neighborhoods
UNION ALL
SELECT 'parks', COUNT(*) FROM core.parks
UNION ALL
SELECT 'schools', COUNT(*) FROM core.schools
ORDER BY dataset;

SELECT
    COUNT(*) FILTER (WHERE NOT ST_IsValid(geom)) AS invalid_geometries,
    COUNT(*) FILTER (WHERE ST_IsEmpty(geom)) AS empty_geometries,
    COUNT(*) FILTER (WHERE ST_SRID(geom) <> 4326) AS wrong_srid
FROM core.neighborhoods;

SELECT
    COUNT(*) FILTER (WHERE NOT ST_IsValid(geom)) AS invalid_geometries,
    COUNT(*) FILTER (WHERE ST_IsEmpty(geom)) AS empty_geometries,
    COUNT(*) FILTER (WHERE ST_SRID(geom) <> 4326) AS wrong_srid
FROM core.parks;

SELECT
    COUNT(*) FILTER (WHERE geom IS NULL) AS missing_geometry,
    COUNT(*) FILTER (WHERE ST_SRID(geom) <> 4326) AS wrong_srid,
    COUNT(*) FILTER (WHERE status_type <> 'Active') AS non_active_rows
FROM core.schools;

SELECT COUNT(*) AS source_registry_rows
FROM metadata.source_registry;

SELECT
    ir.ingestion_run_id,
    sr.source_key,
    ir.status,
    ir.rows_read,
    ir.rows_loaded,
    ir.rows_rejected,
    ir.started_at,
    ir.completed_at
FROM metadata.ingestion_runs AS ir
JOIN metadata.source_registry AS sr USING (source_id)
ORDER BY ir.ingestion_run_id DESC
LIMIT 10;

SELECT COUNT(*) AS schools_inside_san_jose_neighborhoods
FROM app.san_jose_active_schools_spatial;

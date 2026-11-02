\pset pager off

WITH expected(schema_name, relation_name, expected_type) AS (
    VALUES
        ('core', 'neighborhoods', 'BASE TABLE'),
        ('core', 'parks', 'BASE TABLE'),
        ('core', 'schools', 'BASE TABLE'),
        ('app', 'school_neighborhoods', 'VIEW'),
        ('app', 'san_jose_active_schools_spatial', 'VIEW'),
        ('app', 'open_park_neighborhood_intersections', 'VIEW')
)
SELECT
    e.schema_name,
    e.relation_name,
    e.expected_type,
    t.table_type AS actual_type,
    (t.table_name IS NOT NULL AND t.table_type = e.expected_type) AS passed
FROM expected AS e
LEFT JOIN information_schema.tables AS t
  ON t.table_schema = e.schema_name
 AND t.table_name = e.relation_name
ORDER BY e.schema_name, e.relation_name;

WITH required_columns(schema_name, relation_name, column_name) AS (
    VALUES
        ('core', 'neighborhoods', 'enterprise_id'),
        ('core', 'neighborhoods', 'neighborhood_name'),
        ('core', 'neighborhoods', 'geom'),
        ('core', 'parks', 'facility_id'),
        ('core', 'parks', 'park_name'),
        ('core', 'parks', 'current_status'),
        ('core', 'parks', 'geom'),
        ('core', 'schools', 'cds_code'),
        ('core', 'schools', 'school_name'),
        ('core', 'schools', 'education_level_code'),
        ('core', 'schools', 'geom'),
        ('app', 'school_neighborhoods', 'neighborhood_id'),
        ('app', 'san_jose_active_schools_spatial', 'neighborhood_id'),
        ('app', 'open_park_neighborhood_intersections', 'intersection_area_m2')
)
SELECT
    r.schema_name,
    r.relation_name,
    r.column_name,
    (c.column_name IS NOT NULL) AS passed
FROM required_columns AS r
LEFT JOIN information_schema.columns AS c
  ON c.table_schema = r.schema_name
 AND c.table_name = r.relation_name
 AND c.column_name = r.column_name
ORDER BY r.schema_name, r.relation_name, r.column_name;

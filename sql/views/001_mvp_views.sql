CREATE OR REPLACE VIEW app.active_schools AS
SELECT *
FROM core.schools
WHERE status_type = 'Active'
  AND school_name IS NOT NULL
  AND geom IS NOT NULL;

CREATE OR REPLACE VIEW app.school_neighborhoods AS
SELECT
    s.cds_code,
    s.school_name,
    s.district_name,
    s.city AS source_city,
    n.enterprise_id AS neighborhood_id,
    n.neighborhood_name
FROM app.active_schools s
JOIN core.neighborhoods n
  ON ST_Within(s.geom, n.geom);

CREATE OR REPLACE VIEW app.san_jose_active_schools_spatial AS
SELECT s.*, sn.neighborhood_id, sn.neighborhood_name
FROM app.active_schools s
JOIN app.school_neighborhoods sn USING (cds_code);

CREATE OR REPLACE VIEW app.open_park_neighborhood_intersections AS
SELECT
    p.facility_id,
    p.park_name,
    p.park_type_code,
    p.park_class_code,
    n.enterprise_id AS neighborhood_id,
    n.neighborhood_name,
    ST_Area(
        ST_Intersection(p.geom, n.geom)::geography
    ) AS intersection_area_m2
FROM core.parks p
JOIN core.neighborhoods n
  ON ST_Intersects(p.geom, n.geom)
WHERE p.current_status = 'Open';

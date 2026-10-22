CREATE INDEX IF NOT EXISTS idx_neighborhoods_geom
    ON core.neighborhoods USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_parks_geom
    ON core.parks USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_schools_geom
    ON core.schools USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_parks_status
    ON core.parks (current_status);

CREATE INDEX IF NOT EXISTS idx_parks_type_class
    ON core.parks (park_type_code, park_class_code);

CREATE INDEX IF NOT EXISTS idx_schools_status_city
    ON core.schools (status_type, city);

CREATE INDEX IF NOT EXISTS idx_schools_district
    ON core.schools (district_name);

CREATE INDEX IF NOT EXISTS idx_schools_level
    ON core.schools (education_level_code);

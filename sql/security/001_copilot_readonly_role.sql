\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'agenticdb_reader'
    ) THEN
        CREATE ROLE agenticdb_reader
            NOLOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOREPLICATION
            NOBYPASSRLS;
    END IF;
END
$$;

ALTER ROLE agenticdb_reader
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

GRANT CONNECT ON DATABASE agenticdb_sj TO agenticdb_reader;
GRANT USAGE ON SCHEMA core, app TO agenticdb_reader;
REVOKE ALL ON SCHEMA metadata FROM agenticdb_reader;

-- Reset and then grant only the relations approved by the copilot catalog.
REVOKE ALL ON ALL TABLES IN SCHEMA core, app, metadata FROM agenticdb_reader;
GRANT SELECT ON TABLE
    core.neighborhoods,
    core.parks,
    core.schools,
    app.school_neighborhoods,
    app.san_jose_active_schools_spatial,
    app.open_park_neighborhood_intersections
TO agenticdb_reader;

GRANT agenticdb_reader TO agenticdb;

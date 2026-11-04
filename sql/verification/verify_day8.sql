\pset pager off
\set ON_ERROR_STOP on

WITH checks AS (
    SELECT
        'readonly_role_exists'::text AS check_name,
        EXISTS (
            SELECT 1 FROM pg_roles WHERE rolname = 'agenticdb_reader'
        ) AS passed

    UNION ALL

    SELECT
        'readonly_role_cannot_login',
        NOT COALESCE((
            SELECT rolcanlogin
            FROM pg_roles
            WHERE rolname = 'agenticdb_reader'
        ), true)

    UNION ALL

    SELECT
        'application_user_is_member',
        pg_has_role('agenticdb', 'agenticdb_reader', 'MEMBER')

    UNION ALL

    SELECT
        'core_schema_usage',
        has_schema_privilege('agenticdb_reader', 'core', 'USAGE')

    UNION ALL

    SELECT
        'app_schema_usage',
        has_schema_privilege('agenticdb_reader', 'app', 'USAGE')

    UNION ALL

    SELECT
        'metadata_schema_not_available',
        NOT has_schema_privilege('agenticdb_reader', 'metadata', 'USAGE')

    UNION ALL

    SELECT
        'schools_select_allowed',
        has_table_privilege('agenticdb_reader', 'core.schools', 'SELECT')

    UNION ALL

    SELECT
        'parks_select_allowed',
        has_table_privilege('agenticdb_reader', 'core.parks', 'SELECT')

    UNION ALL

    SELECT
        'neighborhood_view_select_allowed',
        has_table_privilege(
            'agenticdb_reader',
            'app.school_neighborhoods',
            'SELECT'
        )

    UNION ALL

    SELECT
        'schools_insert_denied',
        NOT has_table_privilege('agenticdb_reader', 'core.schools', 'INSERT')

    UNION ALL

    SELECT
        'parks_update_denied',
        NOT has_table_privilege('agenticdb_reader', 'core.parks', 'UPDATE')

    UNION ALL

    SELECT
        'neighborhood_delete_denied',
        NOT has_table_privilege(
            'agenticdb_reader',
            'core.neighborhoods',
            'DELETE'
        )

    UNION ALL

    SELECT
        'geography_index_exists',
        EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'core'
              AND tablename = 'parks'
              AND indexname = 'idx_parks_geom_geography_gist'
        )
)
SELECT check_name, passed
FROM checks
ORDER BY check_name;

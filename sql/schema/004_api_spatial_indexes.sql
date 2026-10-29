CREATE INDEX IF NOT EXISTS idx_parks_open_geography
ON core.parks
USING GIST ((geom::geography))
WHERE current_status = 'Open';

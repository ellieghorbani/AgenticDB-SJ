# Open Decisions Before Milestone 2

## 1. How should “San Jose school” be defined?

Two defensible definitions produce different counts in this snapshot:

- Source field `City = San Jose`: 214 active school records.
- Spatially inside the supplied neighborhood polygons: 220 active school records.

Recommendation: load all active school points and create a transparent spatial view. Add an official city-limit polygon later so that neighborhood coverage is not used as a substitute for a legal municipal boundary.

## 2. What counts as a park?

The Park dataset contains conventional parks, trails, school playgrounds, libraries, community gardens, county/open-space facilities, future sites, closed sites, and one seasonal family camp. The database should retain every source record. User-facing views must state their filters explicitly, for example:

- `open_park_facilities`
- `open_trails`
- `open_conventional_parks`
- `future_park_sites`

Do not invent a mapping from source codes to friendly categories until the official code/domain definitions are captured.

## 3. How should parks be assigned to neighborhoods?

A park polygon may intersect more than one neighborhood. Avoid forcing a one-to-one `neighborhood_id` column into the park table. Use a spatial relationship view or bridge table, with optional intersection area and percentage.

## 4. How should invalid neighborhood geometries be handled?

Repair only in the processed layer using `make_valid`; never modify the raw file. Store a Boolean `geom_repaired` flag and preserve the source identifiers and original checksum.

## 5. Should historical schools be loaded?

For the MVP application, use active schools. For provenance and future historical questions, either retain the entire source file in a staging table or make the raw snapshot reproducibly reloadable. Do not mix closed and active schools in the default view.

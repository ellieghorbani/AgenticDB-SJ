# Day 4 Query Notes

## Fixed benchmark scope

The benchmark is tied to the real-data snapshot loaded in Day 3:

- 297 San José neighborhood polygons
- 611 park-dataset features
- 10,537 active California school records
- 220 active schools spatially inside the supplied neighborhood polygons
- 526 park-dataset features whose source status is `Open`

The phrase **open park feature** is intentionally precise. The source dataset also contains trails, libraries, school properties, community gardens, and other facility types. We do not invent a conventional-park category without an official source-code definition.

## Why write gold SQL before adding an LLM?

The ten queries establish trusted answers. Later, when the agent generates SQL, its returned primary keys and values can be compared with these gold outputs. This separates database correctness from agent correctness.

## Concepts demonstrated

### Q01 — `LEFT JOIN` and aggregation

Keeps all neighborhoods, including those containing zero schools. `COUNT(DISTINCT cds_code)` prevents accidental duplication.

### Q02 — polygon intersection aggregation

Uses the existing park-neighborhood intersection view and counts distinct source feature IDs.

### Q03 — nearest neighbor plus a radius condition

Uses `CROSS JOIN LATERAL` to calculate one nearest open feature per elementary school. Casting geometry to `geography` makes distance units meters.

### Q04 — deterministic nearest neighbor

Returns exactly one row per school. `facility_id` is a secondary sort key for deterministic behavior if two features have equal distance.

### Q05 — fixed spatial intersection case

Uses the unique neighborhood ID for Almaden Lake rather than relying on a potentially duplicated name.

### Q06 — avoiding many-to-many overcounting

School and park counts are aggregated independently before they are joined. Directly joining schools, parks, and neighborhoods would multiply rows.

### Q07 — valid empty result

The current snapshot has no in-scope school farther than one mile from an open source feature. The zero-row answer is useful for testing agent behavior.

### Q08 — nearest-neighbor aggregation

Calculates one distance per school first, then aggregates those distances by neighborhood.

### Q09 — radius join

`ST_DWithin` performs a one-mile spatial join. `COUNT(DISTINCT cds_code)` protects against duplicate counting.

### Q10 — conditional aggregation

PostgreSQL's `FILTER` clause counts source-coded elementary (`ELEM`) and high-school (`HS`) records separately.

## Important units

- Source geometry SRID: 4326
- Distance calculation type: `geography`
- One mile: `1609.344` meters
- Intersection area: square meters

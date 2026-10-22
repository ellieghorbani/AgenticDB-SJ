# AgenticDB-SJ Milestone 1: Real-Data Audit

**Snapshot date:** 2026-10-16  
**Scope:** parks, neighborhoods, and public schools  
**Policy:** no fabricated domain records

## Executive finding

The three files are suitable for the first relational and spatial version of AgenticDB-SJ. The source identifiers are unique, the school file contains usable coordinates for every active school record, and the park geometries are valid. The neighborhood file requires a documented repair step for 11 self-intersecting polygons before PostGIS loading.

## Files received

| Dataset | Rows/features | Columns | Format | SHA-256 |
|---|---:|---:|---|---|
| San Jose parks | 611 | 35 | GeoJSON | `cd34c5d2756666b29a3ab6f92f586565a67d520364bcced43ebc96d260cf23d2` |
| San Jose neighborhoods | 297 | 11 | GeoJSON | `e668337e85b901fbf3a34b889d0a1f67a567eeabaaa2b46bee17484e59111104` |
| California public schools and districts | 18,409 | 46 | Tab-delimited text | `7416f452ea14d2b887f0bd9e3a065ff32d611017f32a1841b0f5c4413e232bb3` |

## Parks audit

- The snapshot contains **611 features**: 553 Polygon and 58 MultiPolygon geometries.
- CRS is **EPSG:4326**.
- All **611 geometries are valid**.
- `FACILITYID`, `OBJECTID`, and `INTID` are unique and non-null in this snapshot.
- `NAME` is not unique: **14 name values** are used by multiple source features. Use `FACILITYID`, not name, as the key.
- Status distribution: Open: 526, Closed: 36, Future Park: 30, Future Park (unsecured): 9, Under Construction: 5, Design: 2, Construction: 1, Permit: 1, Seasonal: 1.
- **604** park features intersect at least one neighborhood polygon; **7** do not.
- The dataset includes more than conventional neighborhood parks: trails, school playgrounds, libraries, community gardens, county/open-space facilities, and a seasonal family camp. Load all source rows, then expose well-defined views for each user-facing category.

## Neighborhood audit

- The snapshot contains **297 features**: 274 Polygon and 23 MultiPolygon geometries.
- CRS is **EPSG:4326**.
- **11 polygons are invalid** because of ring self-intersections. Shapely `make_valid` repairs all 11 without losing polygonal geometry.
- `ENTERPRISEID`, `FACILITYID`, `OBJECTID`, and `INTID` are unique and non-null.
- Names are not unique: `Commercial` and `Guadalupe` each occur twice. Use `ENTERPRISEID` as the primary source key.
- After repair, the polygons are effectively non-overlapping. Only one pair has a positive overlap greater than 1 square meter, and that overlap is approximately **2.319 m²**, consistent with a very small boundary artifact.

## School audit

- The file contains **18,409 statewide rows** and **46 columns**.
- `CDSCode` is unique for all rows and must remain a string.
- Source status counts: Active: 11,596, Closed: 5,368, Merged: 1,441, Pending: 4.
- **1,394 rows** have `School = No Data`; they represent district or non-school entities and should not appear in the school application view.
- There are **10,537 active school rows statewide**, and all have parseable latitude and longitude.
- The source city field identifies **214 active schools** in San Jose.
- A spatial point-in-polygon join identifies **220 active schools** inside the supplied neighborhood polygons. Six have mailing-city labels other than San Jose: Campbell (3), Morgan Hill (1), Alviso (1), and Los Gatos (1).
- Every one of the 214 active records whose source city is San Jose falls inside exactly one neighborhood polygon. No active school point matched multiple neighborhoods.

## Required decisions before database loading

1. **Geographic scope:** Load all active California school records, then define San Jose through a spatial view. This is more transparent than permanently deleting records based on the mailing-city field. For a production-quality boundary, add an official San Jose city-limit dataset later.
2. **Meaning of “park”:** Keep all 611 source features, then create separate views for open parks, trails, school playgrounds, and other facility classes. Do not silently treat every feature as a conventional park.
3. **Neighborhood repairs:** Use `make_valid`, log the 11 repaired IDs, and set `geom_repaired = true`.
4. **Keys:** Use `CDSCode` for schools, `FACILITYID` for park features, and `ENTERPRISEID` for neighborhoods. Names are labels, not keys.
5. **Missing values:** Convert the CDE literal `No Data` to SQL `NULL` only in curated tables; keep the raw text snapshot unchanged.

## Recommended next milestone

Create the PostgreSQL/PostGIS database and implement reproducible loaders in this order:

1. Create metadata, core, and application schemas.
2. Load source-registry and ingestion-run records.
3. Load repaired neighborhoods.
4. Load parks without filtering source records.
5. Load active schools as points.
6. Create spatial indexes.
7. Create San Jose school and park/neighborhood relationship views.
8. Validate the first ten relational and spatial questions with ordinary SQL before adding an LLM.

## Files in this package

- `data/manifests/data_sources.yaml`: provenance, checksums, and snapshot information
- `data/profiles/*.csv`: column-level profiles and exception lists
- `docs/data_dictionary/*.md`: field inventories and transformation rules
- `docs/decisions/open_decisions.md`: design decisions found during the audit
- `ingestion/audit_datasets.py`: reproducible audit script
- `ingestion/prepare_data.py`: deterministic cleaning and derived-scope script
- `sql/schema/*.sql`: initial PostGIS schema and indexes
- `sql/views/001_mvp_views.sql`: first curated spatial views
- `tests/test_data_contracts.py`: snapshot and data-quality tests
- `results/audit_summary.json`: machine-readable audit results

# San Jose Neighborhoods Data Dictionary

## Source

- Publisher: City of San Jose
- Dataset: Neighborhoods
- Raw snapshot: `data/raw/san_jose/neighborhoods/neighborhoods_2026-10-16.geojson`

## Snapshot summary

- Records: **297**
- CRS: **EPSG:4326**
- Geometry: **274 Polygon, 23 MultiPolygon**
- Geometry validity before repair: **286 valid, 11 invalid**
- Geometry validity after `make_valid`: **297 valid**
- Unique `ENTERPRISEID`: **297**
- Unique names: **295**; `Commercial` and `Guadalupe` each occur twice.

## Field inventory

| Source field | Proposed database field | Source type | Missing % | Unique non-missing |
|---|---|---:|---:|---:|
| `OBJECTID` | `objectid` | `int32` | 0.00% | 297 |
| `FACILITYID` | `facilityid` | `object` | 0.00% | 297 |
| `INTID` | `intid` | `int32` | 0.00% | 297 |
| `NAME` | `name` | `object` | 0.00% | 295 |
| `SOURCE` | `source` | `object` | 61.62% | 3 |
| `LASTUPDATE` | `lastupdate` | `datetime64[ms, UTC]` | 0.00% | 8 |
| `NOTES` | `notes` | `object` | 97.64% | 7 |
| `ENTERPRISEID` | `enterpriseid` | `object` | 0.00% | 297 |
| `SHAPE_Length` | `shape_length` | `float64` | 0.00% | 297 |
| `SHAPE_Area` | `shape_area` | `float64` | 0.00% | 297 |
| `geometry` | `geom` | `geometry` | 0.00% | 297 |

## Transformation rules

- Retain every source feature and use `ENTERPRISEID` as the primary source key.
- Repair the 11 self-intersecting geometries with Shapely `make_valid` and record `geom_repaired = true`.
- Convert Polygon and MultiPolygon inputs to `MULTIPOLYGON` during database loading.
- Do not use neighborhood name as a key because `Commercial` and `Guadalupe` each occur twice.

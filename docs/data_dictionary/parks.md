# San Jose Parks Data Dictionary

## Source

- Publisher: City of San Jose
- Dataset: Park
- Raw snapshot: `data/raw/san_jose/parks/parks_2026-10-16.geojson`

## Snapshot summary

- Records: **611**
- CRS: **EPSG:4326**
- Geometry: **553 Polygon, 58 MultiPolygon**
- Geometry validity: **611 valid, 0 invalid**
- Unique `FACILITYID`: **611**
- Unique names: **591**; 14 name values are repeated across multiple features.

## Field inventory

| Source field | Proposed database field | Source type | Missing % | Unique non-missing |
|---|---|---:|---:|---:|
| `OBJECTID` | `objectid` | `int32` | 0.00% | 611 |
| `FACILITYID` | `facilityid` | `object` | 0.00% | 611 |
| `INTID` | `intid` | `int32` | 0.00% | 611 |
| `GISOBJID` | `gisobjid` | `float64` | 32.90% | 396 |
| `NAME` | `name` | `object` | 0.00% | 591 |
| `ADDRESS` | `address` | `object` | 8.51% | 508 |
| `PARKTYPE` | `parktype` | `object` | 0.00% | 23 |
| `PARKCLASS` | `parkclass` | `object` | 0.00% | 5 |
| `SUBCLASS` | `subclass` | `object` | 0.00% | 24 |
| `CURRENTSTATUS` | `currentstatus` | `object` | 0.00% | 9 |
| `DATEOPENED` | `dateopened` | `datetime64[ms, UTC]` | 74.63% | 99 |
| `DEEDDATE` | `deeddate` | `datetime64[ms, UTC]` | 91.98% | 46 |
| `COUNCILDISTRICT` | `councildistrict` | `float64` | 0.33% | 10 |
| `PARKDISTRICT` | `parkdistrict` | `float64` | 24.88% | 8 |
| `ALLACRES` | `allacres` | `float64` | 3.44% | 463 |
| `DEVACRES` | `devacres` | `float64` | 4.09% | 315 |
| `UNDEVACRES` | `undevacres` | `float64` | 4.09% | 34 |
| `OSACRES` | `osacres` | `float64` | 4.75% | 166 |
| `WATERACRES` | `wateracres` | `float64` | 4.42% | 2 |
| `OWNER` | `owner` | `object` | 3.27% | 55 |
| `NAMEALIAS` | `namealias` | `object` | 22.91% | 357 |
| `LOCATIONID` | `locationid` | `object` | 22.59% | 415 |
| `PLANNINGAREA` | `planningarea` | `object` | 3.93% | 19 |
| `SPPLANAREA` | `spplanarea` | `object` | 80.03% | 25 |
| `PANELNUMBER` | `panelnumber` | `object` | 6.87% | 47 |
| `HYPERLINK` | `hyperlink` | `object` | 59.74% | 223 |
| `ADOPTABLE` | `adoptable` | `object` | 54.01% | 3 |
| `ADOPTIONSTATUS` | `adoptionstatus` | `object` | 55.65% | 2 |
| `PARKCOUNT` | `parkcount` | `object` | 55.81% | 2 |
| `MAINTBY` | `maintby` | `object` | 21.60% | 2 |
| `CONTRACT` | `contract` | `object` | 31.59% | 3 |
| `LASTUPDATE` | `lastupdate` | `datetime64[ms, UTC]` | 0.00% | 154 |
| `SHAPE_Length` | `shape_length` | `float64` | 0.00% | 611 |
| `SHAPE_Area` | `shape_area` | `float64` | 0.00% | 611 |
| `geometry` | `geom` | `geometry` | 0.00% | 611 |

## Transformation rules

- Retain every source feature and use `FACILITYID` as the stable source key for this snapshot.
- Convert both Polygon and MultiPolygon inputs to `MULTIPOLYGON` during database loading.
- Keep status and type codes as source attributes; create user-facing categories in a separate view rather than overwriting the raw values.
- Do not treat `NAME` as a key because multiple source features share the same name.
- Do not silently discard facilities outside the neighborhood extent; flag them through a spatial-scope view.

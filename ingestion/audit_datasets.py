from __future__ import annotations

from pathlib import Path
import hashlib
import json

import geopandas as gpd
import pandas as pd
from shapely import make_valid
from shapely.validation import explain_validity

ROOT = Path(__file__).resolve().parents[1]
PARKS = ROOT / "data/raw/san_jose/parks/parks_2026-10-16.geojson"
NEIGHBORHOODS = ROOT / "data/raw/san_jose/neighborhoods/neighborhoods_2026-10-16.geojson"
SCHOOLS = ROOT / "data/raw/cde/public_schools/public_schools_2026-10-16.txt"
RESULTS = ROOT / "results"
PROFILES = ROOT / "data/profiles"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    PROFILES.mkdir(parents=True, exist_ok=True)

    parks = gpd.read_file(PARKS)
    neighborhoods = gpd.read_file(NEIGHBORHOODS)
    schools = pd.read_csv(SCHOOLS, sep="\t", dtype=str, low_memory=False)

    invalid = neighborhoods.loc[~neighborhoods.geometry.is_valid].copy()
    invalid["reason"] = invalid.geometry.apply(explain_validity)
    invalid[["OBJECTID", "FACILITYID", "ENTERPRISEID", "NAME", "reason"]].to_csv(
        PROFILES / "neighborhood_invalid_geometries.csv", index=False
    )

    repaired = neighborhoods.copy()
    repaired["geometry"] = repaired.geometry.apply(
        lambda geom: make_valid(geom) if geom is not None and not geom.is_valid else geom
    )

    active = schools[(schools["StatusType"] == "Active") & (schools["School"] != "No Data")].copy()
    active["latitude_num"] = pd.to_numeric(active["Latitude"], errors="coerce")
    active["longitude_num"] = pd.to_numeric(active["Longitude"], errors="coerce")
    active = active.dropna(subset=["latitude_num", "longitude_num"])
    active_points = gpd.GeoDataFrame(
        active,
        geometry=gpd.points_from_xy(active["longitude_num"], active["latitude_num"]),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(
        active_points,
        repaired[["ENTERPRISEID", "NAME", "geometry"]],
        predicate="within",
        how="inner",
    )

    summary = {
        "files": {
            "parks_sha256": sha256(PARKS),
            "neighborhoods_sha256": sha256(NEIGHBORHOODS),
            "schools_sha256": sha256(SCHOOLS),
        },
        "parks": {
            "rows": len(parks),
            "crs": str(parks.crs),
            "invalid_geometries": int((~parks.geometry.is_valid).sum()),
            "unique_facility_ids": int(parks["FACILITYID"].nunique()),
        },
        "neighborhoods": {
            "rows": len(neighborhoods),
            "crs": str(neighborhoods.crs),
            "invalid_before_repair": int((~neighborhoods.geometry.is_valid).sum()),
            "invalid_after_repair": int((~repaired.geometry.is_valid).sum()),
            "unique_enterprise_ids": int(neighborhoods["ENTERPRISEID"].nunique()),
        },
        "schools": {
            "source_rows": len(schools),
            "unique_cds_codes": int(schools["CDSCode"].nunique()),
            "active_school_rows": len(active),
            "active_city_san_jose": int((active["City"].str.casefold() == "san jose").sum()),
            "active_inside_neighborhoods": int(joined["CDSCode"].nunique()),
        },
    }

    (RESULTS / "audit_summary_rerun.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

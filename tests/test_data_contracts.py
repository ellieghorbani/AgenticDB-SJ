from pathlib import Path
import hashlib

import geopandas as gpd
import pandas as pd
from shapely import make_valid

ROOT = Path(__file__).resolve().parents[1]
PARKS = ROOT / "data/raw/san_jose/parks/parks_2026-10-16.geojson"
NEIGHBORHOODS = ROOT / "data/raw/san_jose/neighborhoods/neighborhoods_2026-10-16.geojson"
SCHOOLS = ROOT / "data/raw/cde/public_schools/public_schools_2026-10-16.txt"

EXPECTED_HASHES = {
    PARKS: "cd34c5d2756666b29a3ab6f92f586565a67d520364bcced43ebc96d260cf23d2",
    NEIGHBORHOODS: "e668337e85b901fbf3a34b889d0a1f67a567eeabaaa2b46bee17484e59111104",
    SCHOOLS: "7416f452ea14d2b887f0bd9e3a065ff32d611017f32a1841b0f5c4413e232bb3",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_snapshot_hashes():
    for path, expected in EXPECTED_HASHES.items():
        assert digest(path) == expected


def test_park_contract():
    parks = gpd.read_file(PARKS)
    assert len(parks) == 611
    assert parks.crs.to_epsg() == 4326
    assert parks["FACILITYID"].is_unique
    assert parks.geometry.is_valid.all()


def test_neighborhood_contract_and_repair():
    neighborhoods = gpd.read_file(NEIGHBORHOODS)
    assert len(neighborhoods) == 297
    assert neighborhoods.crs.to_epsg() == 4326
    assert neighborhoods["ENTERPRISEID"].is_unique
    assert int((~neighborhoods.geometry.is_valid).sum()) == 11
    repaired = neighborhoods.geometry.apply(
        lambda geom: make_valid(geom) if not geom.is_valid else geom
    )
    assert repaired.is_valid.all()


def test_school_contract():
    schools = pd.read_csv(SCHOOLS, sep="\t", dtype=str, low_memory=False)
    assert len(schools) == 18409
    assert schools["CDSCode"].is_unique
    active = schools[(schools["StatusType"] == "Active") & (schools["School"] != "No Data")].copy()
    lat = pd.to_numeric(active["Latitude"], errors="coerce")
    lon = pd.to_numeric(active["Longitude"], errors="coerce")
    assert len(active) == 10537
    assert lat.notna().all()
    assert lon.notna().all()

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import make_valid
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = ROOT / "data/processed"


def polygonal_multipolygon(geom):
    if geom is None:
        return None
    geom = make_valid(geom) if not geom.is_valid else geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, GeometryCollection):
        polygons = []
        for part in geom.geoms:
            if isinstance(part, Polygon):
                polygons.append(part)
            elif isinstance(part, MultiPolygon):
                polygons.extend(list(part.geoms))
        if polygons:
            return MultiPolygon(polygons)
    raise ValueError(f"Expected polygonal geometry; received {geom.geom_type}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    parks = gpd.read_file(RAW / "san_jose/parks/parks_2026-10-16.geojson")
    parks.columns = [column.lower() if column != "geometry" else column for column in parks.columns]
    parks["geometry"] = parks.geometry.apply(polygonal_multipolygon)
    parks.to_file(OUT / "parks_clean.geojson", driver="GeoJSON")

    neighborhoods = gpd.read_file(
        RAW / "san_jose/neighborhoods/neighborhoods_2026-10-16.geojson"
    )
    neighborhoods["geom_repaired"] = ~neighborhoods.geometry.is_valid
    neighborhoods["geometry"] = neighborhoods.geometry.apply(polygonal_multipolygon)
    neighborhoods.columns = [
        column.lower() if column != "geometry" else column for column in neighborhoods.columns
    ]
    neighborhoods.to_file(OUT / "neighborhoods_clean.geojson", driver="GeoJSON")

    schools = pd.read_csv(
        RAW / "cde/public_schools/public_schools_2026-10-16.txt",
        sep="\t",
        dtype=str,
        low_memory=False,
    )
    schools = schools.replace("No Data", pd.NA)
    schools = schools[(schools["StatusType"] == "Active") & schools["School"].notna()].copy()
    schools["latitude"] = pd.to_numeric(schools["Latitude"], errors="coerce")
    schools["longitude"] = pd.to_numeric(schools["Longitude"], errors="coerce")
    schools = schools.dropna(subset=["latitude", "longitude"])
    school_points = gpd.GeoDataFrame(
        schools,
        geometry=gpd.points_from_xy(schools["longitude"], schools["latitude"]),
        crs="EPSG:4326",
    )

    # Create two explicit, non-destructive scope candidates.
    school_points.loc[
        school_points["City"].str.casefold() == "san jose"
    ].to_file(OUT / "schools_active_city_san_jose.geojson", driver="GeoJSON")

    spatial = gpd.sjoin(
        school_points,
        neighborhoods[["enterpriseid", "facilityid", "name", "geometry"]].rename(
            columns={
                "enterpriseid": "neighborhood_enterprise_id",
                "facilityid": "neighborhood_facility_id",
                "name": "neighborhood_name",
            }
        ),
        predicate="within",
        how="inner",
    ).drop(columns=["index_right"])
    spatial.to_file(OUT / "schools_active_inside_neighborhoods.geojson", driver="GeoJSON")

    print(f"Wrote {len(parks)} cleaned park features")
    print(f"Wrote {len(neighborhoods)} cleaned neighborhood features")
    print(
        "Wrote "
        f"{(school_points['City'].str.casefold() == 'san jose').sum()} source-city San Jose schools"
    )
    print(f"Wrote {spatial['CDSCode'].nunique()} schools inside neighborhood polygons")


if __name__ == "__main__":
    main()

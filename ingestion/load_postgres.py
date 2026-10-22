from __future__ import annotations

import argparse
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import geopandas as gpd
import pandas as pd
import psycopg
import yaml
from dotenv import load_dotenv
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data/manifests/data_sources.yaml"
PROCESSED = ROOT / "data/processed"
RAW = ROOT / "data/raw"
CODE_VERSION = "day3-loader-v1"


def clean(value: Any) -> Any | None:
    """Convert pandas/GeoPandas null-like values to Python None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        value = value.strip()
        if value in {"", "<NA>", "No Data"}:
            return None
    return value


def as_text(value: Any) -> str | None:
    value = clean(value)
    return None if value is None else str(value)


def as_int(value: Any) -> int | None:
    value = clean(value)
    return None if value is None else int(float(value))


def as_float(value: Any) -> float | None:
    value = clean(value)
    return None if value is None else float(value)


def as_date(value: Any) -> date | None:
    value = clean(value)
    if value is None:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


def as_datetime(value: Any) -> datetime | None:
    value = clean(value)
    if value is None:
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else parsed.to_pydatetime()


def geometry_wkt(value: Any) -> str:
    if value is None or value.is_empty:
        raise ValueError("Geometry must be non-empty")
    return value.wkt


def connection_kwargs() -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    required = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_PORT"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing values in .env: {', '.join(missing)}")

    return {
        "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "port": int(os.environ["POSTGRES_PORT"]),
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }


def ensure_schema_exists(conn: psycopg.Connection[Any]) -> None:
    required = [
        "metadata.source_registry",
        "metadata.ingestion_runs",
        "core.neighborhoods",
        "core.parks",
        "core.schools",
    ]
    with conn.cursor() as cur:
        for relation in required:
            cur.execute("SELECT to_regclass(%s)", (relation,))
            if cur.fetchone()[0] is None:
                raise RuntimeError(
                    f"Required relation {relation!r} does not exist. "
                    "Run the Day 2 schema SQL files first."
                )


def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def register_sources(
    conn: psycopg.Connection[Any], manifest: dict[str, Any]
) -> dict[str, int]:
    source_ids: dict[str, int] = {}
    statement = """
        INSERT INTO metadata.source_registry (
            source_key, publisher, dataset_name, source_url, local_file,
            file_format, retrieved_at, file_sha256, row_count, usage_terms
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_key) DO UPDATE SET
            publisher = EXCLUDED.publisher,
            dataset_name = EXCLUDED.dataset_name,
            source_url = EXCLUDED.source_url,
            local_file = EXCLUDED.local_file,
            file_format = EXCLUDED.file_format,
            retrieved_at = EXCLUDED.retrieved_at,
            file_sha256 = EXCLUDED.file_sha256,
            row_count = EXCLUDED.row_count,
            usage_terms = EXCLUDED.usage_terms
        RETURNING source_id
    """
    with conn.cursor() as cur:
        for item in manifest["sources"]:
            cur.execute(
                statement,
                (
                    item["source_key"],
                    item["publisher"],
                    item["dataset_name"],
                    item["landing_page"],
                    item["local_file"],
                    item["format"],
                    item["retrieved_at"],
                    item["sha256"],
                    item.get("row_count"),
                    item.get("usage_terms"),
                ),
            )
            source_ids[item["source_key"]] = cur.fetchone()[0]
    return source_ids


def start_run(conn: psycopg.Connection[Any], source_id: int, rows_read: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO metadata.ingestion_runs (
                source_id, rows_read, status, code_version
            )
            VALUES (%s, %s, 'started', %s)
            RETURNING ingestion_run_id
            """,
            (source_id, rows_read, CODE_VERSION),
        )
        return cur.fetchone()[0]


def finish_run(
    conn: psycopg.Connection[Any],
    run_id: int,
    rows_loaded: int,
    rows_rejected: int = 0,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE metadata.ingestion_runs
            SET completed_at = now(),
                rows_loaded = %s,
                rows_rejected = %s,
                status = 'succeeded',
                error_message = NULL
            WHERE ingestion_run_id = %s
            """,
            (rows_loaded, rows_rejected, run_id),
        )


def fail_run(conn: psycopg.Connection[Any], run_id: int, error: Exception) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE metadata.ingestion_runs
            SET completed_at = now(),
                status = 'failed',
                error_message = %s
            WHERE ingestion_run_id = %s
            """,
            (str(error)[:4000], run_id),
        )


def insert_rows(
    conn: psycopg.Connection[Any],
    *,
    table: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    source_id: int,
    geometry_column: str = "geom",
) -> int:
    schema_name, table_name = table.split(".", maxsplit=1)
    table_identifier = sql.Identifier(schema_name, table_name)

    value_expressions = [
        sql.SQL("ST_GeomFromText(%s, 4326)")
        if column == geometry_column
        else sql.Placeholder()
        for column in columns
    ]

    insert_statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        table_identifier,
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        sql.SQL(", ").join(value_expressions),
    )
    delete_statement = sql.SQL("DELETE FROM {} WHERE source_id = %s").format(
        table_identifier
    )
    count_statement = sql.SQL("SELECT COUNT(*) FROM {} WHERE source_id = %s").format(
        table_identifier
    )

    with conn.cursor() as cur:
        cur.execute(delete_statement, (source_id,))
        cur.executemany(insert_statement, rows)
        cur.execute(count_statement, (source_id,))
        return cur.fetchone()[0]


def run_loader(
    conn: psycopg.Connection[Any],
    *,
    label: str,
    source_id: int,
    rows_read: int,
    operation: Callable[[], int],
) -> int:
    run_id = start_run(conn, source_id, rows_read)
    try:
        with conn.transaction():
            loaded = operation()
            finish_run(conn, run_id, loaded)
        print(f"Loaded {loaded:,} {label} records")
        return loaded
    except Exception as exc:
        fail_run(conn, run_id, exc)
        raise


def prepare_neighborhood_rows(source_id: int) -> list[tuple[Any, ...]]:
    path = PROCESSED / "neighborhoods_clean.geojson"
    frame = gpd.read_file(path)
    if frame.crs is None or frame.crs.to_epsg() != 4326:
        raise ValueError(f"Unexpected neighborhood CRS: {frame.crs}")
    if not frame["enterpriseid"].is_unique:
        raise ValueError("Neighborhood enterpriseid is not unique")
    if not frame.geometry.is_valid.all():
        raise ValueError("Neighborhood geometries must be valid before loading")

    rows: list[tuple[Any, ...]] = []
    for record in frame.to_dict(orient="records"):
        rows.append(
            (
                as_text(record["enterpriseid"]),
                as_text(record["facilityid"]),
                as_int(record["objectid"]),
                as_int(record["intid"]),
                as_text(record["name"]),
                as_text(record.get("source")),
                as_datetime(record.get("lastupdate")),
                as_text(record.get("notes")),
                as_float(record.get("shape_length")),
                as_float(record.get("shape_area")),
                bool(record.get("geom_repaired", False)),
                geometry_wkt(record["geometry"]),
                source_id,
            )
        )
    return rows


def prepare_park_rows(source_id: int) -> list[tuple[Any, ...]]:
    path = PROCESSED / "parks_clean.geojson"
    frame = gpd.read_file(path)
    if frame.crs is None or frame.crs.to_epsg() != 4326:
        raise ValueError(f"Unexpected park CRS: {frame.crs}")
    if not frame["facilityid"].is_unique:
        raise ValueError("Park facilityid is not unique")
    if not frame.geometry.is_valid.all():
        raise ValueError("Park geometries must be valid before loading")

    rows: list[tuple[Any, ...]] = []
    for record in frame.to_dict(orient="records"):
        rows.append(
            (
                as_text(record["facilityid"]),
                as_int(record["objectid"]),
                as_int(record["intid"]),
                as_float(record.get("gisobjid")),
                as_text(record["name"]),
                as_text(record.get("address")),
                as_text(record["parktype"]),
                as_text(record["parkclass"]),
                as_text(record["subclass"]),
                as_text(record["currentstatus"]),
                as_date(record.get("dateopened")),
                as_date(record.get("deeddate")),
                as_int(record.get("councildistrict")),
                as_int(record.get("parkdistrict")),
                as_float(record.get("allacres")),
                as_float(record.get("devacres")),
                as_float(record.get("undevacres")),
                as_float(record.get("osacres")),
                as_float(record.get("wateracres")),
                as_text(record.get("owner")),
                as_text(record.get("namealias")),
                as_text(record.get("locationid")),
                as_text(record.get("planningarea")),
                as_text(record.get("spplanarea")),
                as_text(record.get("panelnumber")),
                as_text(record.get("hyperlink")),
                as_text(record.get("adoptable")),
                as_text(record.get("adoptionstatus")),
                as_text(record.get("parkcount")),
                as_text(record.get("maintby")),
                as_text(record.get("contract")),
                as_datetime(record.get("lastupdate")),
                as_float(record.get("shape_length")),
                as_float(record.get("shape_area")),
                geometry_wkt(record["geometry"]),
                source_id,
            )
        )
    return rows


def prepare_school_rows(source_id: int) -> tuple[list[tuple[Any, ...]], int]:
    path = RAW / "cde/public_schools/public_schools_2026-10-16.txt"
    frame = pd.read_csv(path, sep="\t", dtype=str, low_memory=False)
    raw_count = len(frame)
    frame = frame.replace("No Data", pd.NA)
    frame = frame[(frame["StatusType"] == "Active") & frame["School"].notna()].copy()
    frame["latitude_numeric"] = pd.to_numeric(frame["Latitude"], errors="coerce")
    frame["longitude_numeric"] = pd.to_numeric(frame["Longitude"], errors="coerce")
    frame = frame.dropna(subset=["latitude_numeric", "longitude_numeric"])
    frame = frame[
        frame["latitude_numeric"].between(-90, 90)
        & frame["longitude_numeric"].between(-180, 180)
    ].copy()

    if not frame["CDSCode"].is_unique:
        raise ValueError("CDSCode is not unique after school filtering")

    rows: list[tuple[Any, ...]] = []
    for record in frame.to_dict(orient="records"):
        point_wkt = f"POINT({record['longitude_numeric']} {record['latitude_numeric']})"
        rows.append(
            (
                as_text(record["CDSCode"]),
                as_text(record.get("NCESDist")),
                as_text(record.get("NCESSchool")),
                as_text(record["StatusType"]),
                as_text(record["County"]),
                as_text(record["District"]),
                as_text(record.get("School")),
                as_text(record.get("Street")),
                as_text(record.get("City")),
                as_text(record.get("Zip")),
                as_text(record.get("State")),
                as_text(record.get("Phone")),
                as_text(record.get("WebSite")),
                as_date(record.get("OpenDate")),
                as_date(record.get("ClosedDate")),
                as_text(record.get("Charter")),
                as_text(record.get("CharterNum")),
                as_text(record.get("FundingType")),
                as_text(record.get("DOC")),
                as_text(record.get("DOCType")),
                as_text(record.get("SOC")),
                as_text(record.get("SOCType")),
                as_text(record.get("EdOpsCode")),
                as_text(record.get("EdOpsName")),
                as_text(record.get("EILCode")),
                as_text(record.get("EILName")),
                as_text(record.get("GSoffered")),
                as_text(record.get("GSserved")),
                as_text(record.get("Virtual")),
                as_text(record.get("Magnet")),
                as_text(record.get("YearRoundYN")),
                as_text(record.get("FederalDFCDistrictID")),
                as_text(record.get("Multilingual")),
                as_date(record.get("LastUpDate")),
                point_wkt,
                source_id,
            )
        )
    print(
        f"Selected {len(rows):,} active school records with valid coordinates "
        f"from {raw_count:,} source rows"
    )
    return rows, raw_count


NEIGHBORHOOD_COLUMNS = [
    "enterprise_id",
    "facility_id",
    "object_id",
    "internal_id",
    "neighborhood_name",
    "source_method",
    "source_last_updated",
    "notes",
    "source_shape_length",
    "source_shape_area",
    "geom_repaired",
    "geom",
    "source_id",
]

PARK_COLUMNS = [
    "facility_id",
    "object_id",
    "internal_id",
    "gis_object_id",
    "park_name",
    "address",
    "park_type_code",
    "park_class_code",
    "subclass_code",
    "current_status",
    "date_opened",
    "deed_date",
    "council_district",
    "park_district",
    "all_acres",
    "developed_acres",
    "undeveloped_acres",
    "open_space_acres",
    "water_acres",
    "owner",
    "name_alias",
    "location_id",
    "planning_area",
    "specific_plan_area",
    "panel_number",
    "hyperlink",
    "adoptable_code",
    "adoption_status",
    "park_count_code",
    "maintained_by_code",
    "contract_code",
    "source_last_updated",
    "source_shape_length",
    "source_shape_area",
    "geom",
    "source_id",
]

SCHOOL_COLUMNS = [
    "cds_code",
    "nces_district_id",
    "nces_school_id",
    "status_type",
    "county_name",
    "district_name",
    "school_name",
    "street",
    "city",
    "zip_code",
    "state",
    "phone",
    "website",
    "open_date",
    "closed_date",
    "charter_code",
    "charter_number",
    "funding_type",
    "district_ownership_code",
    "district_ownership_type",
    "school_ownership_code",
    "school_ownership_type",
    "education_option_code",
    "education_option_name",
    "education_level_code",
    "education_level_name",
    "grades_offered",
    "grades_served",
    "virtual_code",
    "magnet_code",
    "year_round_code",
    "federal_district_id",
    "multilingual_code",
    "source_last_updated",
    "geom",
    "source_id",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load AgenticDB-SJ real datasets into PostgreSQL/PostGIS."
    )
    parser.add_argument(
        "--only",
        choices=["all", "neighborhoods", "parks", "schools"],
        default="all",
        help="Load all datasets or only one dataset.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = load_manifest()

    with psycopg.connect(**connection_kwargs(), autocommit=True) as conn:
        ensure_schema_exists(conn)
        source_ids = register_sources(conn, manifest)

        if args.only in {"all", "neighborhoods"}:
            source_id = source_ids["san_jose_neighborhoods"]
            rows = prepare_neighborhood_rows(source_id)
            run_loader(
                conn,
                label="neighborhood",
                source_id=source_id,
                rows_read=len(rows),
                operation=lambda: insert_rows(
                    conn,
                    table="core.neighborhoods",
                    columns=NEIGHBORHOOD_COLUMNS,
                    rows=rows,
                    source_id=source_id,
                ),
            )

        if args.only in {"all", "parks"}:
            source_id = source_ids["san_jose_parks"]
            rows = prepare_park_rows(source_id)
            run_loader(
                conn,
                label="park",
                source_id=source_id,
                rows_read=len(rows),
                operation=lambda: insert_rows(
                    conn,
                    table="core.parks",
                    columns=PARK_COLUMNS,
                    rows=rows,
                    source_id=source_id,
                ),
            )

        if args.only in {"all", "schools"}:
            source_id = source_ids["california_public_schools"]
            rows, _raw_count = prepare_school_rows(source_id)
            run_loader(
                conn,
                label="school",
                source_id=source_id,
                rows_read=len(rows),
                operation=lambda: insert_rows(
                    conn,
                    table="core.schools",
                    columns=SCHOOL_COLUMNS,
                    rows=rows,
                    source_id=source_id,
                ),
            )

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM core.neighborhoods) AS neighborhoods,
                    (SELECT COUNT(*) FROM core.parks) AS parks,
                    (SELECT COUNT(*) FROM core.schools) AS schools,
                    (SELECT COUNT(*) FROM app.san_jose_active_schools_spatial)
                        AS schools_inside_san_jose_neighborhoods
                """
            )
            counts = cur.fetchone()

    print("\nDatabase totals")
    print(f"  neighborhoods: {counts[0]:,}")
    print(f"  parks: {counts[1]:,}")
    print(f"  active schools: {counts[2]:,}")
    print(f"  schools inside San Jose neighborhoods: {counts[3]:,}")


if __name__ == "__main__":
    main()

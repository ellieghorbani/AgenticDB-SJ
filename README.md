# AgenticDB-SJ — Milestone 1 Data Foundation

This package contains the completed first milestone for the AgenticDB-SJ project: a reproducible audit of three real public datasets.

## Data included

- City of San Jose Park GeoJSON snapshot
- City of San Jose Neighborhoods GeoJSON snapshot
- California Department of Education Public Schools and Districts tab-delimited snapshot

The raw files are copied byte-for-byte from the uploaded archive and their SHA-256 hashes are recorded in `data/manifests/data_sources.yaml`.

## Key result

The datasets are suitable for the relational and spatial MVP. Before loading into PostGIS, repair 11 neighborhood polygons and preserve source identifiers. Do not start the LLM component until the normal SQL/PostGIS queries pass.

## Set up

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Re-run the audit

```bash
python ingestion/audit_datasets.py
```

## Prepare deterministic processed files

```bash
python ingestion/prepare_data.py
```

This writes cleaned derivatives under `data/processed/` while leaving `data/raw/` unchanged.

## Run data-contract tests

```bash
pytest -q
```

## Read first

1. `docs/dataset_audit.md`
2. `docs/decisions/open_decisions.md`
3. `data/manifests/data_sources.yaml`
4. `sql/schema/001_extensions_and_metadata.sql`
5. `sql/schema/002_core_tables.sql`

## Next milestone

Start PostgreSQL/PostGIS, run the schema files, and build a loader that records every ingestion run. Then validate ten ordinary SQL and spatial questions before adding the natural-language agent.

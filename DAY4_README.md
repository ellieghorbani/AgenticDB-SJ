# Day 4 — Gold SQL and PostGIS Benchmark

## Goal

Write, execute, validate, and save ten trusted SQL/PostGIS answers before building the natural-language agent.

## Files added

```text
benchmarks/day4/query_catalog.json
sql/benchmark/q01_...sql through q10_...sql
sql/verification/verify_day4.sql
scripts/run_day4_gold.py
scripts/validate_day4_gold.py
docs/day4_query_notes.md
results/gold/day4/
```

## Run one query manually first

```bash
docker exec -i agenticdb_sj_postgis \
  psql -v ON_ERROR_STOP=1 \
  -U agenticdb \
  -d agenticdb_sj \
  < sql/benchmark/q01_active_schools_per_neighborhood.sql
```

Inspect the output. The query should return 297 neighborhood rows, and the highest school count should be 6.

## Export all ten gold results

Activate the local Python environment:

```bash
source .venv/bin/activate
```

Then run:

```bash
python scripts/run_day4_gold.py
```

This writes ten CSVs and a manifest under:

```text
results/gold/day4/
```

The script runs in a read-only transaction, applies a 60-second statement timeout, verifies the fixed data snapshot, checks expected row counts, and records execution time and SHA-256 hashes.

## Validate exported results

```bash
python scripts/validate_day4_gold.py
```

Expected output:

```text
Day 4 gold-result validation PASSED
Validated 10 CSV files and all cross-query invariants.
```

## Run direct SQL verification

```bash
docker exec -i agenticdb_sj_postgis \
  psql -v ON_ERROR_STOP=1 \
  -U agenticdb \
  -d agenticdb_sj \
  < sql/verification/verify_day4.sql
```

Every row in the `passed` column should be `t`.

## Expected fixed-snapshot results

| Query | Expected rows |
|---|---:|
| Q01 | 297 |
| Q02 | 297 |
| Q03 | 131 |
| Q04 | 220 |
| Q05 | 6 |
| Q06 | 15 |
| Q07 | 0 |
| Q08 | 134 |
| Q09 | 20 |
| Q10 | 18 |

## Commit Day 4

```bash
git add \
  DAY4_README.md \
  benchmarks/day4 \
  docs/day4_query_notes.md \
  scripts/run_day4_gold.py \
  scripts/validate_day4_gold.py \
  sql/benchmark \
  sql/verification/verify_day4.sql \
  results/gold/day4

git commit -m "Add validated SQL and PostGIS gold benchmark"
```

# AgenticDB-SJ Day 3 Files

Copy these files into the project root:

- `ingestion/load_postgres.py`
- `sql/verification/verify_day3.sql`

Add these packages to `requirements.txt`:

```text
psycopg[binary]>=3.2
python-dotenv>=1.0
```

Then activate the project virtual environment, install requirements, and run:

```bash
python ingestion/load_postgres.py
```

Verify the load:

```bash
docker exec -i agenticdb_sj_postgis \
  psql -v ON_ERROR_STOP=1 -U agenticdb -d agenticdb_sj \
  < sql/verification/verify_day3.sql
```

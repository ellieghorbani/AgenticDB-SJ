# Day 8: Independent SQL AST Validation and Controlled Execution

## Objective

Day 8 introduces a second safety boundary between SQL generation and database
execution. Day 7's deterministic generator still produces parameterized SQL,
but Day 8 does not trust the generator's string-level checks by themselves.
The generated statement is reparsed using SQLGlot's PostgreSQL dialect and must
pass an independent policy before any query reaches PostgreSQL.

```text
Natural-language question
        ↓
Day 6 typed plan
        ↓
Day 7 parameterized SQL generation
        ↓
Day 8 SQLGlot AST validation
        ↓
Restricted role + read-only transaction
        ↓
Bounded PostgreSQL/PostGIS execution
```

## No raw-SQL API

The validation and execution endpoints accept only:

```json
{
  "question": "...",
  "top_k": 6
}
```

The Pydantic request models reject extra fields. A caller cannot submit an
arbitrary `sql` value through either endpoint.

## Independent AST policy

The Day 8 validator checks:

1. Day 7 actually generated SQL.
2. Placeholder and parameter counts match.
3. SQLGlot can parse the statement as PostgreSQL.
4. Exactly one statement exists.
5. The AST root is a `SELECT` query.
6. No write, DDL, administrative, or execution AST node appears.
7. No row-locking clause appears.
8. All physical relations are schema-qualified.
9. Every relation belongs to the curated schema allowlist.
10. AST relations match Day 7's declared relations.
11. Declared source columns exist in the curated catalog.
12. Every function belongs to a narrow allowlist.
13. No wildcard projection is present.
14. The outer query has a numeric `LIMIT`.
15. The limit does not exceed the configured result-row policy.

The validator also generates a deterministic SHA-256 fingerprint from the SQL
and parameter artifact for evaluation and audit logs.

## Parameter parsing

Psycopg uses `%s` placeholders. SQLGlot parses SQL text, so the validator creates
an internal parse-only copy with each placeholder replaced by a correctly typed
literal. The original parameterized SQL remains unchanged and is the only form
sent to Psycopg.

## Database-level controls

The file `sql/security/001_copilot_readonly_role.sql` creates a NOLOGIN role:

```text
agenticdb_reader
```

It receives:

- `USAGE` on `core` and `app`
- `SELECT` on current and future relations in `core` and `app`
- no access to `metadata`
- no write privileges

The application login role receives membership and the executor uses:

```sql
SET LOCAL ROLE agenticdb_reader;
```

Execution also requires PostgreSQL to report:

```text
transaction_read_only = on
```

The request is bounded by:

- a statement timeout
- a lock timeout
- an AST-verified SQL limit
- a maximum fetch size
- rollback/connection cleanup after every API request

## Endpoints

### Validate generated SQL

```text
POST /api/v1/copilot/validate
```

This returns the Day 7 generation artifact and Day 8 validation report. It does
not execute the query.

### Execute validated SQL

```text
POST /api/v1/copilot/execute
```

The service regenerates and revalidates SQL within the same request. Execution
occurs only when every check passes.

## Evaluation

The offline AST benchmark contains:

- ten supported questions
- three unsafe, unsupported, or unresolved questions
- eight directly tampered SQL artifacts

The live execution benchmark checks the ten trusted Day 4 row counts and verifies
that database execution occurs under `agenticdb_reader` in a read-only transaction.

# Day 7: Deterministic SQL Generation

## Goal

Day 7 converts a validated Day 6 query plan into reviewed, parameterized PostgreSQL/PostGIS SQL. It deliberately does **not** execute generated SQL.

```text
Natural-language question
        ↓
Day 6 typed plan
        ↓
Day 7 deterministic SQL template
        ↓
Static safety checks
        ↓
SQL + parameters for review
```

## Why generation and execution are separated

A generated query is untrusted application output until it passes independent validation. Keeping execution disabled allows the project to test:

- intent-to-template routing,
- relation and column allowlists,
- read-only statement shape,
- parameter binding,
- single-statement enforcement,
- bounded output,
- and unsafe-request blocking.

Day 8 will add parser/AST validation and controlled read-only execution.

## Endpoint

```text
POST /api/v1/copilot/sql
```

Example request:

```json
{
  "question": "Which neighborhoods contain at least three active schools and two open park features?"
}
```

The response contains:

- the original typed plan,
- generated SQL,
- ordered bind parameters,
- referenced relations and source columns,
- safety-check results,
- `execution_allowed: false`.

## Parameterization

Dynamic values are returned separately from SQL. For example:

```sql
WHERE sc.active_school_count >= %s
  AND pc.open_park_feature_count >= %s
```

with:

```json
[
  {"position": 1, "name": "minimum_school_count", "value": 3},
  {"position": 2, "name": "minimum_park_count", "value": 2}
]
```

The API never interpolates user-supplied text into SQL strings.

## Safety checks

Every generated artifact is checked for:

1. supported planner intent,
2. `SELECT` or `WITH` read-only shape,
3. a single statement,
4. absence of write/administrative keywords,
5. placeholder/parameter count agreement,
6. allowlisted relations,
7. allowlisted source columns,
8. coverage of plan-required relations,
9. an explicit result limit,
10. disabled execution permission.

Unsafe, unsupported, and unresolved requests return no SQL.

## Supported intents

The generator covers the ten Day 4 benchmark intents. This deterministic baseline provides reproducible behavior before an LLM-backed provider is introduced.

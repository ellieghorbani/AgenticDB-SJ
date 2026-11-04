# Day 9: Agent routing, tool traces, evidence, and answer synthesis

Day 9 turns the existing planning, SQL-generation, validation, and execution
components into one explicit agent workflow.

## Workflow

```text
Natural-language question
        |
        v
query.plan
        |
        v
route.select
        |
        +---- blocked / unsupported / clarification ----+
        |                                                |
        v                                                v
sql.generate                                      answer.synthesize
        |
        v
sql.validate
        |
        v
sql.execute
        |
        v
answer.synthesize
```

The six tools are fixed and exposed through:

```text
GET /api/v1/copilot/agent/tools
```

## Safety properties

- API clients submit natural-language questions, not SQL.
- Unsafe requests stop before SQL generation.
- Unsupported and ambiguous questions do not execute.
- SQL must pass the Day 7 template checks and the independent Day 8 AST policy.
- PostgreSQL is opened lazily only when the workflow reaches `sql.execute`.
- Execution uses `agenticdb_reader` in a read-only transaction.
- The answer is derived only from returned rows.
- Evidence rows are bounded by `evidence_limit`.
- Every stage records a status, latency, and compact input/output summary.

## Tool-use reliability

The benchmark checks the same ten trusted Day 4 questions plus unsafe,
unsupported, and clarification cases. It validates:

- intent and route selection,
- exact six-tool ordering,
- skipped execution tools for blocked routes,
- expected row counts,
- restricted database role,
- read-only transactions,
- bounded evidence,
- answer presence,
- and query fingerprints for executed runs.

## Evidence model

The response includes a short deterministic answer and selected supporting rows:

```json
{
  "answer": {
    "text": "Found 15 neighborhoods meeting both thresholds...",
    "row_count": 15,
    "evidence": [
      {
        "row_number": 1,
        "values": {
          "neighborhood_name": "Mayfair",
          "active_school_count": 6,
          "open_park_feature_count": 4
        }
      }
    ],
    "sources": [
      "app.open_park_neighborhood_intersections",
      "app.school_neighborhoods",
      "core.neighborhoods"
    ],
    "query_fingerprint": "..."
  }
}
```

The deterministic synthesizer does not add facts that are absent from the
returned database rows.

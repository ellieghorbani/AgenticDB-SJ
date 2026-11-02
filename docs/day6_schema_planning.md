# Day 6 Schema Retrieval and Structured Planning

## Why this layer exists

An LLM should not receive the whole database or immediately emit executable SQL.
Day 6 introduces two controlled stages:

1. **Schema retrieval** selects only relevant allowlisted relations and columns.
2. **Structured planning** converts a supported question into a typed plan.

The plan is explicitly non-executable:

```json
{
  "execution_allowed": false,
  "sql_generated": false
}
```

SQL generation, AST validation, and execution are deferred to later milestones.

## Catalog design

The catalog combines:

- a curated semantic allowlist in `app/copilot/schema_registry.py`; and
- actual relation and column metadata from `information_schema`.

This approach prevents the copilot from seeing system catalogs, internal tables,
or irrelevant source columns while still detecting schema drift.

## Retrieval design

The Day 6 retriever is deterministic and explainable. It ranks relations using:

- normalized question terms;
- relation names and aliases;
- relation descriptions;
- column names and descriptions;
- semantic tags; and
- a small spatial relevance bonus for distance/intersection questions.

It does not use embeddings yet.

## Planner design

The deterministic planner supports the ten Day 4 benchmark intents and two
negative cases. It extracts:

- required relations;
- output fields;
- filters and thresholds;
- grouping and sorting;
- spatial relationships and normalized distance units;
- assumptions and warnings.

It also blocks obvious write/administrative requests before schema retrieval.

## Safety boundary

Day 6 does **not**:

- generate SQL;
- accept SQL from a client;
- execute a plan;
- call an LLM; or
- broaden the database allowlist.

This separation makes each later failure attributable to a specific stage.

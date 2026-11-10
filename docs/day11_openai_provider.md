# Day 11 Design: Hosted LLM Planning with Deterministic Safety

## Objective

Day 11 introduces an actual hosted language model while preserving the trusted
relational, spatial, vector, and SQL-safety layers already validated in Days
4–10.

## Why the model returns a proposal instead of SQL

Allowing a hosted model to directly authorize and execute arbitrary SQL would
collapse generation and security into one component. Day 11 instead uses the
model for the task where it provides the most value: understanding paraphrased
natural language and extracting typed parameters.

The structured proposal contains:

- one supported intent enum,
- confidence,
- count thresholds,
- distance value and unit,
- neighborhood name,
- clarification requirements,
- and a short rationale.

No SQL appears in the proposal.

## Trusted-plan reconstruction

The proposal is converted into a canonical question and processed by the
existing deterministic planner. This ensures the final plan still uses:

- approved relations,
- approved columns,
- reviewed spatial relationships,
- typed filters,
- and the same Pydantic validation rules used by the benchmark baseline.

## Execution chain

```text
OpenAI proposal
  -> deterministic typed plan
  -> parameterized template SQL
  -> SQLGlot AST validation
  -> restricted read-only database role
  -> evidence-backed answer
```

The model cannot remove or override any later stage.

## Deterministic fallback

`OPENAI_FALLBACK_TO_DETERMINISTIC=true` keeps the application available during
provider outages or configuration errors. Responses identify whether OpenAI,
the deterministic baseline, the local safety gate, or deterministic fallback
was used.

## Telemetry

The planning response records:

- provider and model,
- response identifier,
- input, output, and total tokens,
- hosted-model latency,
- fallback status,
- and optional estimated cost.

Cost estimation is disabled by default because prices change. Current rates can
be supplied through environment variables without changing code.

## Embedding providers

The embedding interface now supports:

- local `sentence-transformers/all-MiniLM-L6-v2`, and
- hosted `text-embedding-3-small` with 384 requested dimensions.

Both provider outputs are L2-normalized and stored in the existing
`vector(384)` column. Model-specific keys allow both indexes to coexist for
comparison.

## Benchmark

The live Day 11 benchmark runs thirteen questions:

- ten supported database questions with expected row counts,
- one destructive request,
- one unsupported events request,
- and one ambiguous neighborhood request.

It reports intent accuracy, execution correctness, fallback usage, latency,
token consumption, optional cost, and the deterministic baseline accuracy on
the same wording.

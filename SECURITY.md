# Security Policy

## Safety design

AgenticDB-SJ does not accept raw SQL from API clients. Hosted models do not
authorize execution and do not directly write executable SQL.

Executable queries must pass:

1. a local destructive-request gate,
2. allowlisted typed planning,
3. deterministic parameterized SQL generation,
4. SQLGlot AST parsing and policy checks,
5. bounded row-limit checks,
6. restricted PostgreSQL-role checks,
7. read-only transaction enforcement,
8. statement and lock timeouts.

## Secrets

Keep these only in the ignored `.env` file:

- `OPENAI_API_KEY`
- `POSTGRES_PASSWORD`
- any future hosted-provider credentials

Never include secrets in issues, logs, screenshots, benchmark artifacts, or
Git commits.

## Reporting

For a public portfolio repository, report security issues privately to the
repository owner rather than opening a public issue with exploit details.

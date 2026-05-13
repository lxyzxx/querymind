# QueryMind

QueryMind is a lightweight governed AI2SQL engine.

It demonstrates a production-oriented pattern for natural-language analytics: the LLM maps a user question to governed semantic objects, while deterministic code compiles those objects into SQL and sends the query through execution safeguards.

## Core Idea

Bare Text-to-SQL lets the model guess table names, columns, filters, and metric definitions. QueryMind keeps business logic in a semantic layer:

```text
User question
  -> Agent tool call
  -> metric + dimensions + filters
  -> deterministic SQL compiler
  -> read-only SQL guard
  -> database
```

For example, the model calls `query_metric`:

```json
{
  "metric": "user_count",
  "dimensions": "status",
  "named_filters": "active_only",
  "limit": 20
}
```

The semantic layer compiles it into SQL:

```sql
SELECT status AS status, count(*) AS user_count
FROM public.users
WHERE (status = 'active')
GROUP BY status
ORDER BY user_count DESC
LIMIT 20
```

## Features

- YAML semantic layer for metrics, dimensions, filters, and synonyms.
- Deterministic metric-to-SQL compiler.
- LangChain agent demo with semantic SQL tools.
- Read-only SQL guard:
  - only `SELECT` / `WITH`
  - no multi-statement SQL
  - DDL and DML keywords are rejected
  - row limit is applied
  - statement timeout is set
- Unit tests for semantic SQL compilation and SQL safety checks.

## Project Layout

```text
docs/architecture.md                Design notes and roadmap
python/querymind/agent/             Semantic layer and SQL compiler
python/querymind/example/           Agent demo and semantic layer example
python/tests/                       Unit tests
```

## Quick Start

Install dependencies:

```bash
python3 -m pip install -r python/requirements.txt
python3 -m pip install -r python/requirements-agent.txt
```

Run tests:

```bash
PYTHONPATH=python python3 -m pytest python/tests
```

Run the agent demo from the repository root:

```bash
export DEEPSEEK_API_KEY=your_api_key

python3 python/querymind/example/agent_demo.py \
  "Generate SQL for active user count by status."
```

Run the governed SQL demo:

```bash
export QUERYMIND_PG_HOST=localhost
export QUERYMIND_PG_PORT=5432
export QUERYMIND_PG_DATABASE=postgres
export QUERYMIND_PG_USER=postgres
export QUERYMIND_PG_PASSWORD=your_password

python3 python/querymind/example/agent_demo.py \
  --enable-pg \
  --semantic-layer python/querymind/example/semantic_layer.yaml \
  --print-trace \
  "按用户状态统计用户数，只看活跃用户"
```

Before running against a real database, edit [semantic_layer.yaml](python/querymind/example/semantic_layer.yaml) to match your table and column names.

## Design Notes

QueryMind is intentionally small. It is not a full production data platform yet, but it includes the boundaries that matter for enterprise AI2SQL:

- governed business semantics
- deterministic SQL generation
- read-only execution controls
- tool-call traceability

See [docs/architecture.md](docs/architecture.md) for details and roadmap.

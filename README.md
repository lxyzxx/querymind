# QueryMind

QueryMind is a lightweight governed AI2SQL / NL2Query engine for business data
querying and insight generation.

It demonstrates a production-oriented pattern for natural-language analytics:
the LLM maps a user question to governed semantic objects, deterministic code
compiles those objects into SQL, execution safeguards protect the database, and
the query result can be turned into an explanation and recommended next steps.

QueryMind is not a full ChatBI or BI platform. It does not try to own dashboards,
drag-and-drop reports, chart builders, or dataset management. It is the core
query and analysis chain that can sit inside ChatBI, a data Q&A assistant, or an
internal intelligent analytics system.

## Core Idea

Bare Text-to-SQL lets the model guess table names, columns, filters, and metric definitions. QueryMind keeps business logic in a semantic layer:

```text
User question
  -> Agent tool call
  -> metric + dimensions + filters
  -> deterministic SQL compiler
  -> read-only SQL guard
  -> database
  -> explanation + suggestions
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
- Structured query and analysis path for data assistants.
- Read-only SQL guard:
  - AST-based validation with `sqlglot`
  - only `SELECT` / `WITH`
  - no multi-statement SQL
  - DDL and DML keywords are rejected
  - semantic-layer table allowlist
  - row limit is applied
  - statement timeout is set
- Golden-question evaluation for deterministic regression checks.
- Unit tests for semantic SQL compilation, SQL safety checks, and evaluation.

## Project Layout

```text
docs/architecture.md                Design notes and roadmap
querymind/agent/                    Semantic layer and SQL compiler
querymind/example/                  Agent demo and semantic layer example
tests/                              Unit tests
```

## Quick Start

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-agent.txt
```

Run tests:

```bash
python3 -m pytest tests
```

Run the deterministic golden-question evaluation:

```bash
python3 querymind/example/evaluate_golden.py \
  --semantic-layer querymind/example/semantic_layer.yaml \
  --golden-file querymind/example/golden_questions.yaml
```

Run the agent demo from the repository root:

```bash
export DEEPSEEK_API_KEY=your_api_key

python3 querymind/example/agent_demo.py \
  "Generate SQL for active user count by status."
```

Run the governed SQL demo:

```bash
export QUERYMIND_PG_HOST=localhost
export QUERYMIND_PG_PORT=5432
export QUERYMIND_PG_DATABASE=postgres
export QUERYMIND_PG_USER=postgres
export QUERYMIND_PG_PASSWORD=your_password

python3 querymind/example/agent_demo.py \
  --enable-pg \
  --semantic-layer querymind/example/semantic_layer.yaml \
  --print-trace \
  "按用户状态统计用户数，只看活跃用户"
```

Before running against a real database, edit [semantic_layer.yaml](querymind/example/semantic_layer.yaml) to match your table and column names.

## Design Notes

QueryMind is intentionally small. It is not a full production data platform or a
complete ChatBI application yet, but it includes the boundaries that matter for
enterprise AI2SQL and natural-language data querying:

- governed business semantics
- deterministic SQL generation
- AST-based read-only execution controls
- structured query planning
- result explanation and recommendation generation
- golden-question regression evaluation
- tool-call traceability

See [docs/architecture.md](docs/architecture.md) for details and roadmap.

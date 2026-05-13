# QueryMind Runtime

A lightweight AI2SQL runtime prototype with a governed semantic layer, read-only SQL guard, and persistent Python execution sessions.

This project demonstrates a practical pattern for enterprise data agents: the LLM does not directly write arbitrary SQL for business metrics. Instead, it maps a user question to governed semantic objects such as metrics, dimensions, and filters. A deterministic compiler then generates SQL and sends it through execution safeguards.

## Architecture

```text
User question
  -> LangChain Agent
  -> Semantic layer tools
  -> Metric SQL compiler
  -> Read-only SQL guard
  -> PostgreSQL

Agent
  -> Python runtime tool
  -> QueryMind gRPC server
  -> Long-lived Python worker session
```

## Features

- Persistent Python runtime over gRPC sessions.
- LangChain agent demo with Python and SQL tools.
- YAML-based semantic layer for metrics, dimensions, filters, and synonyms.
- Deterministic metric-to-SQL compiler.
- Read-only SQL execution guard:
  - only `SELECT` / `WITH`
  - no multi-statement SQL
  - blocks DDL and DML keywords
  - row limit
  - statement timeout
- Trace output for model messages, tool calls, generated SQL, and results.

## Why Semantic Layer

Bare Text-to-SQL asks the model to guess physical table names, columns, joins, and business definitions. That is risky in production because metric definitions can drift.

This project uses a semantic layer:

```yaml
metrics:
  - name: user_count
    expr: count(*)

dimensions:
  - name: status
    expr: status

filters:
  - name: active_only
    expr: status = 'active'
```

The model calls `query_metric` with business objects:

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

## Quick Start

Install dependencies:

```bash
python3 -m pip install -r python/requirements.txt
python3 -m pip install -r python/requirements-agent.txt
```

Generate gRPC stubs if needed:

```bash
python3 -m grpc_tools.protoc \
  -I protobuf \
  --python_out=python/querymind/generated \
  --grpc_python_out=python/querymind/generated \
  protobuf/cli.proto
```

Start the runtime server:

```bash
cd python
python3 -m querymind.server.main --config querymind/server/config.yaml
```

Run the agent from the repository root:

```bash
export DEEPSEEK_API_KEY=your_api_key

python3 python/querymind/example/langchain_agent_mvp.py \
  "Use Python to calculate the average of [12, 19, 23, 31]."
```

Run the semantic SQL demo:

```bash
export QUERYMIND_PG_HOST=localhost
export QUERYMIND_PG_PORT=5432
export QUERYMIND_PG_DATABASE=postgres
export QUERYMIND_PG_USER=postgres
export QUERYMIND_PG_PASSWORD=your_password

python3 python/querymind/example/langchain_agent_mvp.py \
  --enable-pg \
  --semantic-layer python/querymind/example/semantic_layer.yaml \
  --print-trace \
  "按用户状态统计用户数，只看活跃用户"
```

Before running against a real database, edit [semantic_layer.yaml](python/querymind/example/semantic_layer.yaml) to match your table and column names.

## Project Layout

```text
protobuf/                         gRPC protocol definition
python/querymind/client/           Python SDK client
python/querymind/server/           gRPC runtime server and worker scheduler
python/querymind/agent/            Semantic layer utilities
python/querymind/example/          Runtime and AI2SQL demos
docs/                              Design and interview notes
```

## Interview Summary

This is a minimal production-oriented AI2SQL prototype. The important part is not just calling an LLM. The project separates:

- agent orchestration
- semantic metric governance
- deterministic SQL generation
- read-only execution controls
- Python runtime session management

That makes it closer to systems such as Snowflake Cortex Analyst, Databricks Genie, dbt Semantic Layer, and ClickHouse AI SQL workflows than a simple prompt-to-SQL demo.


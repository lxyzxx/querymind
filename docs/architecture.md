# Architecture

QueryMind is a lightweight governed AI2SQL engine.

The core design choice is to keep the LLM away from unrestricted SQL generation for business metrics. The model maps a question to semantic objects, and deterministic code compiles those objects into SQL.

## Query Path

```text
User question
  -> LangChain agent
  -> semantic layer tools
  -> metric SQL compiler
  -> read-only SQL guard
  -> PostgreSQL
```

## Components

### Semantic Layer

The semantic layer is defined in YAML. It describes:

- physical tables
- business metrics
- dimensions
- reusable named filters
- synonyms for business language

Example:

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

### SQL Compiler

The compiler turns semantic requests into SQL. For example:

```json
{
  "metric": "user_count",
  "dimensions": "status",
  "named_filters": "active_only"
}
```

becomes:

```sql
SELECT status AS status, count(*) AS user_count
FROM public.users
WHERE (status = 'active')
GROUP BY status
ORDER BY user_count DESC
LIMIT 50
```

### SQL Guard

The PostgreSQL tool applies a basic execution guard:

- only `SELECT` and `WITH`
- no multi-statement SQL
- DDL and DML keywords are rejected
- row limit is applied
- statement timeout is set

## Roadmap

- ClickHouse SQL dialect support
- schema introspection for bootstrapping semantic YAML
- join relationship compilation
- role-based semantic layer filtering
- SQL explain and cost guard
- golden-question evaluation set

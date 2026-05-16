# Architecture

QueryMind is a lightweight governed AI2SQL / NL2Query engine for business data
querying and insight generation.

The core design choice is to keep the LLM away from unrestricted SQL generation
for business metrics. The model maps a question to semantic objects or a
structured query plan, and deterministic code compiles those objects into SQL.

QueryMind is not a complete ChatBI product. It focuses on the natural-language
to governed-query chain, then uses query results to produce business-facing
explanations and suggested next steps.

## Query Path

```text
User question
  -> LangChain agent
  -> query plan
  -> semantic layer tools
  -> metric SQL compiler
  -> read-only SQL guard
  -> PostgreSQL
  -> insight generator
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

### Query Plan

The query plan is the structured bridge between natural language and SQL
compilation. It captures the user's intent before any SQL is produced:

```json
{
  "question_type": "comparison",
  "metric": "sales_amount",
  "dimensions": ["region"],
  "filters": {"month": "current"},
  "comparison": "month_over_month",
  "limit": 50
}
```

Simple fact questions may compile to one SQL statement. Diagnostic questions can
compile to several governed queries across configured breakdown dimensions.

### SQL Guard

The PostgreSQL tool applies a basic execution guard:

- AST-based validation with `sqlglot`
- only `SELECT` and `WITH`
- no multi-statement SQL
- DDL and DML keywords are rejected
- physical tables must be present in the semantic-layer allowlist
- row limit is applied
- statement timeout is set

### Evaluation

Golden questions live in YAML and define the expected semantic request and SQL
for representative business questions. The evaluator compiles each request,
passes the SQL through the same guard used before execution, and reports a
pass rate. This gives a deterministic regression signal when prompts, semantic
definitions, or compiler behavior change.

### Insight Generation

Insight generation turns query results into concise business explanations. This
layer should distinguish observed facts from inferred causes and recommended
actions, so users can trace every conclusion back to the underlying query
results.

## Roadmap

- ClickHouse SQL dialect support
- schema introspection for bootstrapping semantic YAML
- join relationship compilation
- role-based semantic layer filtering
- SQL explain and cost guard
- deterministic query-plan compiler for trend, comparison, and diagnosis
- result-to-insight generation with evidence links
- LLM-in-the-loop evaluation for natural-language-to-semantic-object accuracy

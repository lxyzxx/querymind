# QueryMind Python Package

This directory contains the QueryMind semantic layer, SQL guard, agent demo, and tests.

## Install

From the repository root:

```bash
python3 -m pip install -r python/requirements.txt
python3 -m pip install -r python/requirements-agent.txt
```

## Tests

```bash
PYTHONPATH=python python3 -m pytest python/tests
```

## Agent Demo

Run from the repository root:

```bash
export DEEPSEEK_API_KEY=your_api_key

python3 python/querymind/example/agent_demo.py \
  "Generate SQL for active user count by status."
```

To enable PostgreSQL execution:

```bash
export QUERYMIND_PG_HOST=localhost
export QUERYMIND_PG_PORT=5432
export QUERYMIND_PG_DATABASE=postgres
export QUERYMIND_PG_USER=postgres
export QUERYMIND_PG_PASSWORD=your_password

python3 python/querymind/example/agent_demo.py --enable-pg --print-trace \
  "按用户状态统计用户数，只看活跃用户"
```

Edit `python/querymind/example/semantic_layer.yaml` to match your real table and column names before running it against a real database.


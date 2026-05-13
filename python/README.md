# QueryMind Python Package

This directory contains the QueryMind Python runtime, SDK client, semantic layer utilities, and examples.

## Install

From the repository root:

```bash
python3 -m pip install -r python/requirements.txt
python3 -m pip install -r python/requirements-agent.txt
```

Generate gRPC stubs after changing `protobuf/cli.proto`:

```bash
python3 -m grpc_tools.protoc \
  -I protobuf \
  --python_out=python/querymind/generated \
  --grpc_python_out=python/querymind/generated \
  protobuf/cli.proto
```

## Runtime Server

```bash
cd python
python3 -m querymind.server.main --config querymind/server/config.yaml
```

## SDK Example

```python
from querymind.client import QueryMindClient

client = QueryMindClient("localhost", 50051)
sid = client.open_session()

client.execute(sid, "x = 100")
out = client.execute(sid, "print(x + 23)")
print(out)

client.close_session(sid)
client.close()
```

## LangChain Agent Demo

Run from the repository root:

```bash
export DEEPSEEK_API_KEY=your_api_key

python3 python/querymind/example/langchain_agent_mvp.py \
  "Use Python to calculate the average of [12, 19, 23, 31], store it as avg, and explain the result."
```

To enable PostgreSQL:

```bash
export QUERYMIND_PG_HOST=localhost
export QUERYMIND_PG_PORT=5432
export QUERYMIND_PG_DATABASE=postgres
export QUERYMIND_PG_USER=postgres
export QUERYMIND_PG_PASSWORD=your_password

python3 python/querymind/example/langchain_agent_mvp.py --enable-pg --print-trace \
  "Query the users table in PostgreSQL and summarize the first 5 rows."
```

The optional `execute_sql` tool only allows read-only `SELECT`/`WITH` queries, rejects multi-statement SQL, applies a row limit, and sets a statement timeout.

## Semantic Layer Demo

```bash
python3 python/querymind/example/langchain_agent_mvp.py \
  --enable-pg \
  --semantic-layer python/querymind/example/semantic_layer.yaml \
  --print-trace \
  "按用户状态统计用户数，只看活跃用户"
```

Edit `python/querymind/example/semantic_layer.yaml` to match your real table and column names before running it against a real database.


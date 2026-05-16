# QueryMind

QueryMind 是一个面向业务数据查询的轻量级、受治理的 AI2SQL / NL2Query
引擎，负责把自然语言问题转换为受控、可执行、可追踪的数据库查询，并基于
查询结果生成解释和建议。

QueryMind 不是完整的 ChatBI 或 BI 平台。它不负责仪表盘、拖拽报表、图表
配置或数据集管理，而是 ChatBI、数据问答助手、智能分析系统里的核心查询与
分析链路。

## 核心思路

直接 Text-to-SQL 会让模型猜表名、字段名、过滤条件和指标口径。QueryMind
把业务逻辑放在语义层里：模型负责理解用户问题并选择受治理的语义对象，确定
性代码负责生成 SQL、执行安全校验，并把查询结果转成业务解释和建议。

```text
用户问题
  -> Agent 工具调用 / QueryPlan
  -> 指标 + 维度 + 过滤条件
  -> 确定性 SQL 编译器
  -> 只读 SQL Guard
  -> 数据库
  -> 解释 + 建议
```

例如模型调用 `query_metric`：

```json
{
  "metric": "user_count",
  "dimensions": "status",
  "named_filters": "active_only",
  "limit": 20
}
```

语义层会把它编译成 SQL：

```sql
SELECT status AS status, count(*) AS user_count
FROM public.users
WHERE (status = 'active')
GROUP BY status
ORDER BY user_count DESC
LIMIT 20
```

## 功能

- 用 YAML 定义语义层：指标、维度、过滤器、同义词和物理表映射。
- 确定性的指标到 SQL 编译器。
- `QueryPlan`、`QueryResult`、`Insight` 核心结构。
- 基础的结果解释和建议生成器。
- 可选 LLM 适配层，避免核心逻辑绑定某个模型 SDK。
- LangChain Agent 示例，演示语义 SQL 工具调用。
- 只读 SQL Guard：
  - 基于 `sqlglot` 做 AST 校验
  - 只允许 `SELECT` / `WITH`
  - 禁止多语句 SQL
  - 拒绝 DDL / DML 关键字
  - 基于语义层做表 allowlist
  - 自动限制返回行数
  - 设置 statement timeout
- golden question 评测，用于确定性回归检查。
- 覆盖语义 SQL 编译、SQL 安全校验、评测和核心结构的单元测试。

## 项目结构

```text
docs/architecture.md                架构说明和路线图
querymind/agent/                    现有语义层、SQL 编译器和 Agent demo
querymind/core/                     QueryPlan、QueryResult、Insight 等核心结构
querymind/llm/                      模型无关的 LLM 适配层接口
querymind/server/                   可选 FastAPI 服务骨架
querymind/example/                  示例语义层、Agent demo 和评测样例
tests/                              单元测试
```

## 快速开始

安装核心依赖：

```bash
python3 -m pip install -r requirements.txt
```

如果要运行 Agent demo，再安装 Agent 依赖：

```bash
python3 -m pip install -r requirements-agent.txt
```

运行测试：

```bash
python3 -m pytest tests
```

运行确定性的 golden question 评测：

```bash
python3 querymind/example/evaluate_golden.py \
  --semantic-layer querymind/example/semantic_layer.yaml \
  --golden-file querymind/example/golden_questions.yaml
```

从仓库根目录运行 Agent demo：

```bash
export DEEPSEEK_API_KEY=your_api_key

python3 querymind/example/agent_demo.py \
  "Generate SQL for active user count by status."
```

运行带 PostgreSQL 查询执行的受治理 SQL demo：

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

连接真实数据库前，请先修改
[semantic_layer.yaml](querymind/example/semantic_layer.yaml)，让物理表名和字段
表达式匹配你的数据仓库。

运行可选 HTTP API：

```bash
python3 -m pip install -r requirements-server.txt
uvicorn querymind.server.app:app --reload
```

当前 API：

- `GET /health`
- `POST /compile-sql`
- `POST /insight`

## 设计说明

QueryMind 目前刻意保持小而清晰。它不是完整生产级数据平台，也不是完整
ChatBI 应用，但已经包含企业 AI2SQL / 自然语言数据查询里最关键的边界：

- 受治理的业务语义层
- 确定性 SQL 生成
- 基于 AST 的只读执行控制
- 结构化 QueryPlan
- 查询结果解释和建议生成
- golden question 回归评测
- 工具调用和查询链路可追踪

更多细节和路线图见 [docs/architecture.md](docs/architecture.md)。

# AI2SQL Semantic Layer 面试讲法

## 项目改造一句话

我把 QueryMind 从一个“LLM 调工具执行 Python/SQL”的 MVP，升级成了一个带语义层约束的 AI2SQL 原型：业务问题先映射到指标、维度、过滤器和表关系，再由确定性的编译逻辑生成 SQL，最后经过只读 SQL Guard 执行。

## 为什么要做

裸 Text-to-SQL 的问题是模型直接面对物理表结构，容易出现口径不一致、join 错误、字段误用、权限绕过和不可审计。

我加语义层的目标是让模型不要直接猜 SQL，而是在一个受控的业务语义空间里工作：

- 指标统一：`user_count`、`revenue`、`active_user` 这类指标集中定义。
- 维度统一：业务词映射到真实字段表达式。
- 过滤统一：常用业务过滤器沉淀成命名规则。
- 执行安全：最终 SQL 仍走只读校验、单语句限制、limit 和 statement timeout。
- 可观测：工具返回生成 SQL 和结果，方便 trace、review 和评测。

## 当前架构

```text
用户自然语言
  -> LangChain Agent
  -> describe_semantic_layer / query_metric
  -> SemanticLayer YAML
  -> deterministic SQL compiler
  -> read-only SQL validator
  -> PostgreSQL
```

同时 QueryMind 仍保留原有 Python Runtime：

```text
Agent
  -> execute_python
  -> QueryMind gRPC Server
  -> long-lived Python worker/session
```

所以这个项目可以讲成两个 Runtime：

- Code Runtime：执行 Python，保留 session state。
- SQL Runtime：执行受控 SQL，后续可以接 PostgreSQL、ClickHouse、Hive、Trino。

## 我具体做了什么

新增 `querymind.agent.semantic_layer`：

- 支持从 YAML 加载 semantic model。
- 定义 table、dimension、metric、filter、synonym。
- 支持根据 metric + dimensions + filters 编译 SQL。
- 对 limit 做边界控制。
- 对维度过滤做 SQL literal 转义，避免把用户文本直接拼成未处理 SQL。

改造 `langchain_agent_mvp.py`：

- 增加 `--semantic-layer` 参数。
- 增加 `describe_semantic_layer` 工具。
- 增加 `query_metric` 工具。
- 系统提示里要求业务指标优先走 `query_metric`，只有语义层表达不了时才 fallback 到 `execute_sql`。
- 复用原来的只读 SQL 防护：只允许 `SELECT/WITH`、禁止多语句、禁止 DDL/DML、设置 limit 和 statement timeout。

## 面试中可以怎么说

我不是只做了一个 prompt demo，而是把 AI2SQL 拆成了几层：

第一层是 Agent 编排层，负责理解用户问题并选择工具。

第二层是语义层，负责把业务语言映射到受治理的指标、维度、过滤器和物理表字段。

第三层是 SQL 执行层，负责 SQL 生成、只读校验、超时、limit、结果返回和 trace。

这样做的好处是，模型不直接拼任意 SQL，业务口径可控，SQL 可审计，权限和执行策略也能在中间层统一治理。

## 和 ClickHouse / 业内方案的关系

ClickHouse 25.7 已经支持 AI-powered SQL generation，也有 MCP Server，可以让 AI 客户端探索 schema、生成和执行查询。但工程落地时，仅靠 schema discovery 不够，企业通常还需要 semantic layer。

我的这个项目可以类比为一个轻量版的语义层 SQL Agent：

- 类似 Snowflake Cortex Analyst 的 semantic model。
- 类似 Databricks Genie Space 的 instructions / trusted assets。
- 类似 dbt Semantic Layer / MetricFlow 的 metric-to-SQL 编译。
- 后续可以把 PostgreSQL executor 替换或扩展为 ClickHouse executor。

## 后续可以继续优化

- 增加 schema introspection，自动生成初始 semantic YAML。
- 增加 join relationship 编译，支持跨表指标。
- 接入权限系统，按用户/租户裁剪可见指标和字段。
- 增加 SQL dry-run、explain、cost guard。
- 增加 benchmark/eval，用 golden questions 验证 SQL 正确率。
- 支持 ClickHouse 方言和 MCP 接入。

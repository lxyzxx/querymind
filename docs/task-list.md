# 任务清单

继续开发 QueryMind 前先读这个文件。每次完成、延期或发现新问题后都要更新它，避免下次重新遍历整个 codebase 才能恢复上下文。

## 当前快照

- 项目：QueryMind，一个轻量级、受治理的 AI2SQL / NL2Query 引擎。
- 当前重点：先把 PostgreSQL 单链路跑通，覆盖自然语言 -> QueryPlan -> 语义层 -> PostgreSQL SQL -> SQL Guard -> PostgreSQL 执行 -> insight -> golden questions 回归。
- 最近更新：2026-05-19。

## 当前收敛路线

先不要做多 SQL 方言。近期目标只围绕 PostgreSQL，把完整流程跑通并可回归：

```text
自然语言
  -> QueryPlan / 语义对象
  -> 语义层匹配 metric / dimension / filter
  -> PostgreSQL SQL 编译器
  -> SQL Guard
  -> PostgreSQL 执行
  -> 结果解释 / insight
  -> golden questions 回归测试
```

## 已完成

- [x] YAML 语义层模型：表、维度、指标、命名过滤器、描述、同义词和物理表映射。
- [x] 确定性指标 SQL 编译器：`querymind/agent/semantic_layer.py`。
- [x] 维度精确筛选、列表筛选、空值筛选和基础 SQL 字面量转义。
- [x] 编译 SQL 的 limit 限制。
- [x] 只读 SQL Guard：`querymind/agent/sql_guard.py`。
- [x] 安装依赖时使用 `sqlglot` 做 AST 校验。
- [x] 单语句限制、DDL/DML 拒绝、CTE 场景下的语义层表 allowlist 校验。
- [x] PostgreSQL 执行包装：只读 session、statement timeout、行数限制。
- [x] LangChain / DeepSeek Agent demo，包含语义层描述、SQL 编译和可选 PostgreSQL 查询工具。
- [x] Golden question 评测，用于确定性 SQL 回归检查。
- [x] `QueryPlan`、`QueryResult`、`Insight`、`InsightEvidence` 核心结构。
- [x] 基础规则版 `BasicQueryPlanner`，用于 demo 和测试中的确定性 QueryPlan 生成。
- [x] 基础结果解释生成器 `BasicInsightGenerator`。
- [x] 模型无关 LLM 协议接口，以及可选 Anthropic 适配器。
- [x] FastAPI 服务骨架，包含 health、plan、compile-sql、analyze-demo、insight 等接口。
- [x] 服务端静态 playground 页面。
- [x] PostgreSQL 端到端命令：`querymind/example/run_pg_flow.py`。
- [x] FastAPI 增加 `/analyze-pg`，可走真实 PostgreSQL 查询并生成 insight。
- [x] Demo 语义层增加 GMV / 销售额指标和 `public.querymind_demo_orders` 示例表。
- [x] 修正 `BasicQueryPlanner` 的未知指标兜底行为：未定义指标会返回澄清，不再默认使用第一个指标。
- [x] 增加 GMV 和未知指标澄清的 planner、API、PG 端到端回归测试。
- [x] 增加“上个月销售额比上上个月下降原因”诊断链路：识别 `month_over_month`，按 `channel` 拆解，生成 PostgreSQL 对比 SQL，并基于结果输出主要下降来源和建议。
- [x] 单元测试覆盖语义层、SQL Guard、评测、核心结构、QueryPlan、Insight、LLM contract 和 Server API。
- [x] README 快速开始和项目结构说明。
- [x] 架构说明和路线图：`docs/architecture.md`。

## 进行中 / 需要完善

- [ ] 每次会话结束前维护本任务清单，把已完成事项移动到 `已完成`，把新发现的问题加入对应区域。
- [ ] 决定 `docs/devfix-gateway.html` 是否应该纳入版本控制、移动位置或加入忽略规则。当前它仍是未跟踪文件。
- [ ] README 和架构文档的中英文风格需要统一，目前 README 主要是中文，`docs/architecture.md` 仍是英文。
- [ ] 为 FastAPI 服务补充清晰的本地启动命令和依赖说明。
- [ ] 明确 Anthropic 适配器是否作为正式支持路径，或仅保留为可选示例。
- [ ] 为 `/analyze-pg` 增加更清晰的错误返回，区分语义层错误、SQL Guard 错误和数据库连接错误。
- [ ] 增加更多覆盖完整 PostgreSQL 链路的回归用例或集成测试。
- [ ] 把当前确定性 insight 升级为可选 LLM 分析：输入 QueryPlan、SQL、查询结果和 evidence，让 LLM 生成更自然的原因分析和优化建议。
- [ ] 扩展诊断类问题：同比、最近 N 天、商品/地区/新老客拆解、多指标联动分析。

## 未完成

- [ ] ClickHouse SQL 方言支持。当前明确暂缓，先完成 PostgreSQL 单链路。
- [ ] 从现有数据库做 schema introspection，自动生成语义层 YAML 草稿。
- [ ] 多表 join 关系建模和跨表 SQL 编译。
- [ ] 基于角色的语义层过滤。
- [ ] SQL explain 和成本 guard。
- [ ] trend、comparison、diagnosis 等 QueryPlan 的确定性多查询编译。
- [ ] 带证据链接的结果到 insight 生成。
- [ ] LLM-in-the-loop 评测，用于验证自然语言到语义对象 / QueryPlan 的准确性。
- [ ] 更完整的模型 provider 配置和运行时选择机制。
- [ ] 打包、发布和版本管理流程。
- [ ] 连接真实 PostgreSQL 的集成测试。

## 下次接续步骤

1. 先读本文件。
2. 执行 `git status --short`，确认是否有用户未提交改动。
3. 只阅读和当前任务直接相关的文件。
4. 修改完成后更新本文件：
   - 完成的事项移动到 `已完成`。
   - 新发现的问题加入 `进行中 / 需要完善` 或 `未完成`。
   - 项目状态有实质变化时更新快照日期。

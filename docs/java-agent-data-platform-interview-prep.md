# Java / Agent / Data Platform 面试准备笔记

面向岗位：阿里妈妈数智应用团队，指标平台、DMP、数据 AI 应用、AI Agent 开发与评测优化。

候选人定位建议：

> 我不是纯 CRUD 后端，而是偏数据平台基础设施和运行时方向。过去做过数据库连接层、Query Gateway、JDBC/ODBC、Arrow Flight SQL、ADBC、OAuth2、Session 管理、Query Routing、SQL Cache、Runtime 调度和长生命周期 Worker。现在我正在把这些能力迁移到 Agent 工程化方向：把数据库、SQL 执行、Python Runtime、权限、审计、Tracing、Memory 和 Tool Calling 做成企业级 Agent 平台的基础设施。

核心叙事：

```text
过去经验:
  数据库连接层 / Gateway / Flight SQL / Runtime / OAuth2 / Query Routing

迁移方向:
  Agent Tool Runtime / SQL Agent / 企业 AI 平台 / 数据智能应用

共同底层:
  请求路由、会话管理、执行隔离、权限治理、审计、缓存、稳定性、可观测性
```

不要说：

> 我没做过 Agent。

应该说：

> 我已有数据平台、查询链路和运行时工程经验。Agent 本质上需要 Tool Runtime、Memory、Workflow、权限、可观测和评测体系，这些和我过去做的 Query Gateway、Runtime、Session、OAuth2、Flight SQL Proxy 很接近。我现在重点在补 LangChain/LangGraph、SQL Agent、RAG、Self Reflection 和 Multi-Agent 编排能力。

---

## 0. 岗位理解与面试主线

### 面试官真正想考什么

这个岗位不是单纯 Java 后端，也不是单纯 Prompt 工程。它关注三类能力：

1. Java 后台工程能力：Spring、MyBatis、JVM、稳定性、线上问题排查。
2. 数据平台能力：指标平台、SQL、MySQL、Redis、HBase、查询链路、权限、多租户、缓存。
3. Agent 工程化能力：Agent Harness、Tool Calling、Memory、Workflow、SQL Agent、评测、Tracing、安全治理。

面试官会重点判断：

- 你是不是能独立设计一个企业级数据 AI 应用。
- 你是不是理解从自然语言到 SQL/指标查询的完整链路。
- 你是不是知道 Demo Agent 和企业 Agent 的差距。
- 你是不是能把 Java 后端、数据平台、AI Agent 串成一个系统。
- 你是不是有线上意识：权限、审计、超时、限流、降级、成本、可观测。

### 推荐项目叙事

```text
我过去做的是数据访问和执行基础设施：
  - Gateway 高可用
  - Flight SQL Proxy
  - OAuth2 接入
  - Query Routing
  - Session 管理
  - SQL Cache
  - Runtime 调度

这些能力可以迁移到 Agent 平台：
  - Query Gateway -> Tool Gateway
  - Flight SQL Proxy -> SQL Tool Runtime
  - OAuth2 -> Agent 用户授权与 Tool 权限
  - Session 管理 -> Agent Conversation / Runtime Session
  - Query Routing -> Tool Routing / Model Routing / SQL Routing
  - SQL Cache -> Agent Result Cache / SQL Cache
  - Runtime 调度 -> Code Interpreter / Python Runtime / Sandbox
```

### 面试回答总模板

```text
我会从三层来设计：

第一层是 Agent 编排层，负责理解用户意图、规划步骤、选择工具、维护对话状态。
第二层是 Tool Runtime 层，负责 SQL、Python、指标查询、外部系统 API 的安全执行。
第三层是数据与治理层，负责权限、多租户、审计、缓存、指标口径、Schema 管理和可观测。

我过去做过 Query Gateway、Flight SQL、OAuth2、Session 和 Runtime，这些经验可以复用到 Agent 工程里，因为企业 Agent 真正难点不是调一次模型，而是如何安全、稳定、可控地调用工具和访问数据。
```

---

## 1. Java 基础与 JVM

### 1.1 面试官真正想考什么

Java 基础不是为了背概念，而是看你能不能支撑线上系统：

- 高并发服务为什么会 Full GC。
- Agent 长上下文、Memory、Tool Result 大对象会不会导致堆膨胀。
- Spring 代理、事务、MyBatis 连接池是不是理解。
- Tomcat/NIO 如何承载 Agent API、SQL 查询、长耗时任务。
- 线上 OOM、线程阻塞、连接池耗尽怎么排查。

对于这个岗位，Java 基础要结合：

```text
Agent 平台 API 服务
  -> 长上下文消息
  -> Tool 调用结果
  -> SQL 查询返回大结果
  -> Memory 缓存
  -> Trace 日志
  -> 高并发请求
```

### 1.2 JVM 内存结构

核心结构：

```text
JVM Runtime Data Areas

Thread Shared:
  - Heap
    - Young Gen
    - Old Gen
  - Method Area / Metaspace

Thread Private:
  - JVM Stack
  - Native Method Stack
  - Program Counter
```

面试要结合真实系统：

- Agent messages、SQL result、RAG chunks、tool outputs 通常在堆上。
- 类元数据、动态代理类、CGLIB 生成类在 Metaspace。
- 深递归、复杂表达式解析可能触发 StackOverflow。
- 大量线程会增加线程栈内存，Tomcat 线程池不能无限加。

高分回答：

> 我理解 JVM 内存不是孤立概念。比如 Agent 平台里，一次请求可能携带很长的 messages、schema context、SQL result sample 和 tracing span。如果这些都保存在内存里，容易造成堆膨胀和频繁 GC。所以我会控制 tool result 大小、做上下文压缩、使用 result reference 替代大对象直接进入 prompt，同时对 conversation state 做 TTL 和外部化存储。

### 1.3 GC 与 Full GC

常见 GC 触发原因：

- Young GC：新对象分配频繁，Eden 满。
- Old GC / Full GC：老年代空间不足、Metaspace 不足、显式 `System.gc()`、大对象晋升失败。
- Agent 场景下，大对象常见来源：大 SQL 结果、长 messages、embedding 文本、trace payload。

排查思路：

```text
1. 观察现象
   - RT 抖动
   - CPU 飙高
   - 请求超时
   - Full GC 次数增加

2. 看指标
   - heap used
   - old gen used
   - GC pause
   - allocation rate
   - thread count

3. 拿证据
   - GC log
   - jstat
   - jmap histogram
   - heap dump
   - arthas

4. 定位对象
   - 大 SQL result
   - conversation messages
   - cache 未淘汰
   - trace span 积压
   - thread local 泄漏

5. 修复
   - 限制返回行数
   - 上下文压缩
   - 缓存加 TTL / max size
   - 大结果外部化
   - 修复引用链
```

面试回答模板：

```text
如果线上出现 Full GC，我不会先调 JVM 参数，而是先判断是内存泄漏、瞬时大对象、缓存策略问题还是流量突增。
我会先看 GC log 和监控，确认 Young GC / Full GC 频率、Old 区增长趋势和停顿时间。
然后通过 heap dump 或 jmap histogram 找大对象来源。
在 Agent 场景里，我会重点看 messages、tool result、SQL result、Memory cache、trace buffer 是否无限增长。
修复上优先从业务层限流、截断、TTL、外部化存储入手，再调整堆大小和 GC 参数。
```

常见追问：

- 为什么 Full GC 频繁但堆没有明显泄漏？
- G1 和 CMS 的区别？
- 大对象直接进老年代有什么风险？
- Agent 上下文特别长怎么避免内存爆？

Agent 场景回答：

> Agent 服务里我会避免把完整 SQL 结果、完整文档、完整工具输出直接放入 messages。工具层返回 summary + sample + result_id，完整结果放对象存储或数据库。这样既控制 token，也控制 JVM 堆内存。

### 1.4 OOM 排查

OOM 类型：

```text
java.lang.OutOfMemoryError: Java heap space
java.lang.OutOfMemoryError: Metaspace
java.lang.OutOfMemoryError: unable to create new native thread
GC overhead limit exceeded
Direct buffer memory
```

企业 Agent 平台常见原因：

- 会话状态未释放。
- Tool result cache 没 TTL。
- SQL 查询返回过大。
- RAG 检索结果过多。
- Trace 日志异步队列积压。
- Netty/Arrow DirectBuffer 未释放。
- 每个请求创建线程或连接。

高分回答：

> 我会把 OOM 分为堆、Metaspace、线程、Direct Memory。对于数据平台和 Agent 平台，Direct Memory 也要关注，因为 Flight SQL、Arrow、Netty 都可能用堆外内存。排查时会结合 JVM 参数、GC log、heap dump、native memory tracking 和连接数/线程数指标。

### 1.5 Spring IOC / AOP

面试官想考：

- Spring Bean 生命周期是否理解。
- AOP 动态代理和事务失效是否理解。
- 能不能用 Spring 做企业 Agent 平台的扩展点。

IOC：

```text
配置 / 注解 -> BeanDefinition -> 实例化 -> 属性注入 -> 初始化 -> 放入容器 -> 使用 -> 销毁
```

AOP：

```text
JDK Dynamic Proxy:
  基于接口

CGLIB:
  基于子类
```

常见坑：

- 同类内部方法调用导致事务不生效。
- private/final 方法不能被代理。
- 异步线程里事务上下文丢失。
- 多数据源事务边界不清。

Agent 场景：

```text
@ToolPermissionCheck
@TenantCheck
@AuditLog
@TraceSpan
@RateLimit
@Retryable
```

可以用 AOP 做：

- Tool 调用前权限校验。
- SQL 执行审计。
- Agent 请求 tracing。
- Token 成本统计。
- 限流熔断。

面试模板：

```text
Spring AOP 在企业 Agent 平台里很适合做横切治理，比如工具调用权限、审计、Tracing、租户校验和限流。
但核心执行逻辑不能完全依赖 AOP 黑盒化，关键链路我会显式设计 Tool Gateway / Runtime Gateway，让治理逻辑可观测、可测试。
```

### 1.6 MyBatis

重点：

- 一级缓存、二级缓存。
- 动态 SQL。
- Mapper 代理。
- N+1 查询。
- 批量写入。
- SQL 注入风险。

结合 SQL Agent：

> SQL Agent 生成 SQL 时不能直接拼接用户输入，更不能把模型生成的 SQL 直接交给生产库执行。MyBatis 适合业务固定 SQL；Agent SQL 是动态 SQL，更需要 SQL Parser、AST 校验、只读账号、权限和审计。

常见追问：

- MyBatis `#{}` 和 `${}` 区别？
- 动态 SQL 如何避免注入？
- Mapper 接口为什么不用实现类？
- 分页查询如何优化？

回答重点：

```text
#{}
  预编译参数
  防 SQL 注入

${}
  字符串替换
  有注入风险
  只适合白名单控制的表名、字段名、排序字段
```

### 1.7 Tomcat / NIO

面试官想考：

- Web 容器线程模型。
- 长耗时 Agent 请求会不会占满线程。
- SQL 执行、LLM 调用、Tool 调用如何隔离线程池。

Tomcat 简化模型：

```text
Acceptor -> Poller -> Worker Thread -> Servlet
```

Agent 场景风险：

```text
HTTP request thread
  -> LLM call 10s
  -> SQL call 5s
  -> Python Runtime 20s
```

如果同步阻塞，会很快耗尽 Tomcat 线程池。

高分设计：

```text
API Thread Pool:
  只负责接请求、鉴权、提交任务

Agent Executor Pool:
  负责 Agent workflow

Tool Executor Pool:
  SQL / Python / HTTP tool 分开隔离

Callback / SSE / WebSocket:
  长任务异步返回进度
```

回答模板：

> 对 Agent 平台，我不会让 Tomcat 工作线程长期阻塞在 LLM 或 SQL 调用上。会把请求提交到专门的执行池，返回 task id 或使用 SSE/WebSocket 流式返回。不同工具使用独立线程池和限流策略，避免某类慢工具拖垮整个服务。

### 1.8 本章高频问题

#### 高频问题

- JVM 内存结构是什么？
- Full GC 怎么排查？
- OOM 怎么定位？
- Spring IOC/AOP 原理？
- 动态代理怎么实现？
- MyBatis `#{}` 和 `${}` 区别？
- Tomcat NIO 线程模型？
- Agent 长上下文导致内存压力怎么解决？

#### 面试回答模板

```text
我会先讲原理，再落到线上场景。
比如 JVM 内存，我会重点关注堆、Metaspace、线程栈和 Direct Memory。
在 Agent 平台里，messages、tool result、SQL result、Memory cache 都可能造成内存压力。
所以我会从上下文裁剪、大结果外部化、缓存 TTL、线程池隔离和 GC 监控几个方面治理。
```

#### 高分回答

> JVM 和 Spring 不是孤立知识点。企业 Agent 平台本质上也是 Java 后端系统，只是请求链路里多了 LLM、Tool、Memory、Workflow。长上下文、SQL 大结果、Python Runtime 输出都会变成内存、线程和连接池压力。我的设计会把 Agent 执行和 Web 请求线程解耦，控制上下文大小，给 Tool 调用做线程池隔离、超时和熔断，并通过 GC、trace、metrics 做线上可观测。

#### 常见错误回答

- 只背 JVM 区域，不说线上排查。
- 只说调大堆，不分析对象来源。
- 只说 Spring AOP 原理，不知道事务失效。
- Agent 场景下把所有历史和结果都放 messages。

#### 常见追问

- 如果 SQL result 很大，放到 prompt 里有什么问题？
- 如果 Agent 请求持续 30 秒，Tomcat 线程池怎么设计？
- Flight SQL / Arrow 使用堆外内存，OOM 怎么排查？
- Tool 调用 tracing 用 AOP 还是网关层做？

---

## 2. 数据库与 SQL

### 2.1 面试官真正想考什么

这个岗位有指标平台和 DMP 背景，SQL 能力非常关键。面试官会考：

- MySQL 索引、B+ 树、MVCC、事务隔离。
- SQL explain 和调优。
- Redis、HBase 的使用场景。
- 你能不能设计 SQL Agent 的执行链路。
- 你是否理解 Query Routing、SQL Cache、权限、多租户和审计。

### 2.2 MySQL 索引与 B+ 树

核心知识：

```text
B+ Tree:
  - 非叶子节点存 key
  - 叶子节点存数据或主键
  - 叶子节点有序链表
  - 适合范围查询
```

InnoDB：

```text
聚簇索引:
  主键索引叶子节点存整行数据

二级索引:
  叶子节点存主键值
  需要回表
```

优化点：

- 最左前缀。
- 覆盖索引。
- 避免函数作用在索引列。
- 避免隐式类型转换。
- 控制返回行数。
- 高选择性字段优先。

Agent 场景：

> SQL Agent 生成 SQL 时，不能只追求语义正确，还要考虑索引可用性。比如时间范围、租户 id、业务主键通常应该进入 where 条件。SQL Validation 可以检查是否缺少分区条件、租户条件和 limit。

### 2.3 MVCC 与事务隔离

MVCC 关键：

```text
undo log
read view
trx_id
可见性判断
```

隔离级别：

```text
Read Uncommitted
Read Committed
Repeatable Read
Serializable
```

InnoDB 默认 Repeatable Read，通过 MVCC + next-key lock 解决很多并发问题。

结合 Agent：

- SQL Agent 查询通常使用只读事务。
- 查询类 Agent 不应该持有长事务。
- 大查询要设置 statement timeout。
- Agent 不能自动执行写操作，除非有明确审批和权限。

面试模板：

> 在 SQL Agent 场景里，我会默认使用只读连接或只读事务，避免模型误生成写 SQL。对于长查询，不让它持有长事务，也不会让 Agent 在事务里等待模型调用。数据库事务只包真实 SQL 执行，不包 LLM 推理过程。

### 2.4 Explain 与 SQL 优化

Explain 重点字段：

```text
type
possible_keys
key
rows
filtered
Extra
```

常见 type：

```text
system > const > eq_ref > ref > range > index > ALL
```

常见 Extra：

- Using index：覆盖索引。
- Using where：服务器层过滤。
- Using temporary：临时表。
- Using filesort：额外排序。

SQL Agent 可以使用 Explain 做 Validation：

```text
Generated SQL
  -> Parser / AST Check
  -> EXPLAIN
  -> Cost Guard
  -> Execute
```

拦截规则：

- 没有 where 且扫描大表。
- 缺少 tenant_id。
- 缺少时间分区。
- rows 估算过大。
- 出现全表扫描且没有 limit。
- 有 filesort/temporary 且数据量大。

### 2.5 Redis

常见用途：

- 缓存热点指标。
- 分布式锁。
- 限流计数器。
- 会话状态。
- Agent result cache。
- Embedding/schema 检索结果缓存。

Agent 场景：

```text
SQL Cache:
  key = tenant + normalized_sql + auth_scope + data_version

Tool Result Cache:
  key = tool_name + normalized_args + tenant + user_scope

Conversation Session:
  key = conversation_id
  value = messages summary / runtime_session_id
```

高分点：

> Agent 缓存必须带权限上下文，不能只按 SQL 文本缓存。否则 A 用户有权限查到的数据可能被 B 用户命中缓存。

缓存 key 示例：

```text
cache_key = hash(
  tenant_id,
  user_id_or_role_scope,
  normalized_sql,
  datasource_id,
  schema_version,
  policy_version
)
```

### 2.6 HBase

适合场景：

- 海量 KV。
- 宽表。
- 按 rowkey 范围扫描。
- 高写入吞吐。
- 历史行为明细。
- DMP 用户画像标签。

不适合：

- 复杂 join。
- 多维随机查询。
- 强事务。

Agent 场景：

> 如果 DMP 标签和用户画像存在 HBase，SQL Agent 不能直接让模型随便查 HBase。应该封装成受控 Tool，比如 `get_user_profile(user_id)`、`query_audience_by_tags(tags)`，而不是暴露底层 Scan API。

### 2.7 Query Routing 与 SQL Cache

Query Routing：

```text
SQL Request
  -> Parse
  -> Tenant/Auth Check
  -> Data Source Selection
  -> Read/Write Split
  -> Shard Routing
  -> Engine Routing
  -> Execute
```

在 Agent 平台中：

```text
Natural Language
  -> SQL Agent
  -> Generated SQL
  -> Query Gateway
  -> Routing
  -> DB / OLAP / HBase / Metric Engine
```

SQL Cache：

- Normalized SQL。
- 参数化。
- 权限上下文。
- 数据版本。
- TTL。
- 主动失效。

Tradeoff：

```text
缓存命中率 vs 数据新鲜度
缓存粒度细 vs 管理复杂度
结果缓存 vs 计划缓存
用户级缓存 vs 租户级缓存
```

### 2.8 本章高频问题

#### 高频问题

- MySQL 为什么用 B+ 树？
- 聚簇索引和非聚簇索引区别？
- MVCC 怎么实现？
- Explain 怎么看？
- SQL 慢查询如何优化？
- Redis 缓存穿透、击穿、雪崩怎么解决？
- HBase RowKey 怎么设计？
- SQL Agent 生成慢 SQL 怎么拦？

#### 面试回答模板

```text
SQL 优化我会先看业务语义和数据分布，再看执行计划。
具体会用 explain 看访问类型、索引选择、扫描行数和 Extra。
优化手段包括补索引、改写 SQL、减少回表、控制范围、避免隐式转换、加 limit 和分区条件。
在 SQL Agent 场景里，还要在执行前做 SQL Validation，比如只读校验、权限校验、租户条件校验、Explain cost guard 和 Limit 注入。
```

#### 高分回答

> SQL Agent 不能只解决生成 SQL 的问题，还要解决 SQL 安全和性能问题。我的设计会把 SQL 生成后的链路接到 Query Gateway：先 AST 解析和安全校验，再做权限、多租户、Limit 注入和 Explain cost guard，最后才执行。执行结果也要进入审计和缓存体系。这样 SQL Agent 才能从 Demo 变成企业可用的数据平台能力。

#### 常见错误回答

- 只说加索引。
- SQL Agent 直接执行模型生成 SQL。
- 缓存不带租户和权限。
- 不做 Limit 和 Timeout。
- 不知道 Explain rows 和真实扫描差异。

#### 常见追问

- 模型生成 `select * from big_table` 怎么办？
- SQL Cache 如何避免权限越权？
- NL2SQL 如何处理指标口径？
- 如果 SQL 结果为空，Agent 怎么修复？

---

## 3. Agent 工程

### 3.1 面试官真正想考什么

Agent 工程不是会调用 LangChain 就够了。面试官想看：

- 你是否理解 Agent Harness。
- 你是否知道 LangChain 和 LangGraph 的区别。
- 你是否理解 Tool Calling / Function Calling / JSON Schema。
- 你是否能设计 Memory、RAG、SQL Agent、Self Reflection。
- 你是否知道企业 Agent 的权限、审计、评测、Tracing 和稳定性。

### 3.2 Agent Harness

Agent Harness 可以理解成 Agent 运行框架：

```text
Agent Harness
  - Model Adapter
  - Prompt / System Instruction
  - Tool Registry
  - Tool Executor
  - Memory Manager
  - State Manager
  - Planner / Router
  - Evaluator
  - Tracing
  - Guardrails
```

企业场景不是：

```text
用户问题 -> LLM -> 答案
```

而是：

```text
用户问题
  -> 权限和租户识别
  -> 上下文构造
  -> Tool 选择
  -> Tool 权限校验
  -> Tool 执行
  -> 结果压缩
  -> Self Reflection
  -> 输出
  -> Trace / Audit / Eval
```

### 3.3 LangChain 与 LangGraph

LangChain：

- 高层框架。
- 适合快速构建 tool-calling MVP。
- `create_agent`、tools、model integrations。

LangGraph：

- 底层状态机/图编排框架。
- 适合复杂 workflow、多 Agent、循环、checkpoint、human-in-the-loop。

关系：

```text
LangChain:
  快速搭 Agent

LangGraph:
  显式控制 Agent workflow
```

SQL Agent 更适合 LangGraph：

```text
START
  -> rewrite
  -> schema_retrieval
  -> sql_generation
  -> validation
  -> execution
  -> reflection_or_summary
  -> END
```

失败分支：

```text
validation failed -> reflection -> sql_generation
execution failed -> reflection -> sql_generation
```

### 3.4 OpenClaw / ClaudeCode / Hermes 类工具理解

面试不一定考某个框架 API，而是考你是否理解 Agent Harness 的共性：

```text
模型不是直接输出结果
而是在一个运行框架里:
  - 读取上下文
  - 规划任务
  - 调用工具
  - 观察结果
  - 修正计划
  - 产出答案
```

ClaudeCode / OpenClaw 这类偏工程 Agent 的关键能力：

- 文件系统上下文。
- Shell / Code Tool。
- Patch 应用。
- 多步规划。
- Tool trace。
- 安全边界。
- Human approval。
- Checkpoint / resume。

迁移到企业数据 Agent：

```text
Code tool -> SQL tool / Python runtime
File context -> Schema context / Metric context
Patch trace -> SQL trace / Tool trace
Approval -> SQL 审批 / 高危工具审批
```

### 3.5 MCP

MCP 可以理解成模型访问外部工具和上下文的协议化方式。

核心价值：

- 工具标准化。
- 上下文资源标准化。
- 降低 Agent 与业务系统耦合。
- 支持跨工具生态。

企业 Agent 平台可以设计：

```text
Agent
  -> MCP Server: Metric Catalog
  -> MCP Server: SQL Gateway
  -> MCP Server: User Profile
  -> MCP Server: Python Runtime
```

你可以把过去的 Gateway 经验包装成：

> 我理解 MCP 背后的工程价值是把工具访问标准化。过去我做 Query Gateway、Flight SQL Proxy，本质也是把多种数据库/执行引擎的访问统一到一个受控入口。Agent 时代可以进一步把这些能力封装为 MCP Tool Server。

### 3.6 Memory

Memory 分层：

```text
Short-term Memory:
  当前对话 messages

Working Memory:
  当前任务状态、last_sql、selected_schema、runtime variables

Long-term Memory:
  用户偏好、业务口径、历史查询、常用指标

External Memory:
  Vector DB、Redis、MySQL、对象存储
```

企业治理：

- TTL。
- 租户隔离。
- 用户授权。
- 脱敏。
- 可删除。
- 可审计。
- 上下文压缩。

Agent 场景高分点：

> Memory 不是无限保存聊天记录，而是分层存储和治理。短期上下文用于当前推理，长期记忆用于业务偏好和指标口径，大结果只保存引用。Memory 必须带租户、用户和权限边界。

### 3.7 RAG：BM25 + Vector + Rerank

SQL Agent 的 Schema Retrieval 很适合三阶段：

```text
BM25:
  关键词强匹配
  表名、字段名、注释、指标名

Vector:
  语义召回
  业务描述、历史 SQL、文档

Rerank:
  精排
  判断与问题真正相关的表、字段、join path
```

检索对象：

```text
表名
字段名
字段注释
指标口径
样例值
主外键关系
历史 SQL
业务文档
权限范围
```

Tradeoff：

```text
BM25:
  优点: 精确、可解释、便宜
  缺点: 语义能力弱

Vector:
  优点: 语义召回强
  缺点: 可能召回看似相关但字段不对

Rerank:
  优点: 提升相关性
  缺点: 增加成本和延迟
```

### 3.8 Tool Calling / Function Calling / JSON Schema

Tool 定义应该结构化：

```json
{
  "name": "execute_sql",
  "description": "Execute read-only SQL on approved datasource",
  "parameters": {
    "type": "object",
    "properties": {
      "datasource": {"type": "string"},
      "sql": {"type": "string"},
      "limit": {"type": "integer"}
    },
    "required": ["datasource", "sql"]
  }
}
```

企业 Tool 不能只靠 description：

```text
Tool Registry:
  - name
  - owner
  - schema
  - permission
  - timeout
  - rate limit
  - audit config
  - risk level
  - tenant scope
```

Tool 调用链：

```text
LLM tool_call
  -> JSON Schema Validation
  -> Permission Check
  -> Argument Sanitize
  -> Runtime Execute
  -> Result Compress
  -> Audit / Trace
  -> Return ToolMessage
```

### 3.9 Self Reflection

Self Reflection 不应该是空泛地让模型“再想想”，而是基于证据修复：

```text
SQL syntax error
relation not found
column not found
permission denied
empty result
result too large
timeout
join explosion
```

修复策略：

```text
column not found -> 重新检索 schema
relation not found -> 修正 schema/table
empty result -> 检查过滤条件/时间范围
timeout -> 加条件/limit/改聚合
permission denied -> 返回权限说明，不绕过
```

限制：

```text
max_reflection_attempts = 2
```

否则容易循环。

### 3.10 Multi-Agent

多 Agent 不等于多个模型互聊。企业里更推荐 Supervisor 编排：

```text
Supervisor
  -> Rewrite Agent
  -> Schema Agent
  -> SQL Agent
  -> Validator Agent
  -> Summary Agent
```

通信方式：

```text
单机 MVP:
  LangGraph state

服务化:
  RPC / HTTP

异步分布式:
  MQ: Kafka / RocketMQ / RabbitMQ / Redis Stream

治理增强:
  hooks: before_tool_call / after_tool_call / on_error
```

高分回答：

> 我不会让子 Agent 点对点随便通信，而是通过 Supervisor 和共享 state 传递结构化结果。消息队列适合异步、长任务和分布式部署；hooks 更适合日志、审计、权限和 trace，不是主通信协议。

### 3.11 Agent Evaluation

企业 Agent 必须可评测：

```text
SQL Agent:
  - SQL 可执行率
  - SQL 正确率
  - Schema 命中率
  - 权限违规率
  - 空结果率
  - 修复成功率
  - 平均延迟
  - token 成本

Summary:
  - 忠实度
  - 是否引用真实结果
  - 是否幻觉
```

评测数据：

- 人工标注问题。
- 历史 SQL。
- 指标平台真实查询。
- 边界 case。
- 权限 case。
- 多轮上下文 case。

### 3.12 本章高频问题

#### 高频问题

- LangChain 和 LangGraph 区别？
- Agent Harness 包含什么？
- Tool Calling 和 Function Calling 区别？
- MCP 是什么价值？
- Memory 怎么设计？
- RAG 为什么要 BM25 + Vector + Rerank？
- Self Reflection 怎么避免死循环？
- Multi-Agent 怎么通信？

#### 面试回答模板

```text
我理解 Agent 工程化不是简单 prompt，而是 Harness + Tool Runtime + Memory + Workflow + Governance。
LangChain 适合快速做 tool-calling MVP，LangGraph 适合复杂有状态流程。
企业 Agent 的关键是工具治理、权限、审计、上下文控制、评测和可观测。
我过去做过 Query Gateway、Runtime 和 OAuth2，这些经验可以迁移到 Tool Gateway、Runtime Sandbox 和 Agent 权限体系。
```

#### 高分回答

> Demo Agent 关注模型能不能调用工具，企业 Agent 关注工具能不能安全、稳定、低成本、可观测地运行。我的设计会把 Agent 拆成编排层、工具运行时、Memory 层和治理层。编排层可以用 LangGraph 显式控制流程；工具运行时负责 SQL/Python/API 的隔离执行；治理层负责权限、审计、限流、Tracing 和评测。

#### 常见错误回答

- Agent 等于 LangChain。
- Memory 等于保存所有聊天记录。
- Self Reflection 等于让模型再回答一次。
- Multi-Agent 等于多个模型互相聊天。
- Tool 执行不做权限。

#### 常见追问

- Tool 调用失败怎么处理？
- SQL Agent 怎么防止越权？
- Agent 如何做灰度和回滚？
- 如何评估 SQL Agent 是否真的有效？

---

## 4. SQL Agent 架构设计

### 4.1 面试官真正想考什么

SQL Agent 是这个岗位最容易展开的系统设计题。面试官想看：

- 你是否知道 NL2SQL 不能直接生成 SQL 后执行。
- 你是否理解 Schema Retrieval。
- 你是否知道 SQL 安全、权限、多租户、审计。
- 你是否能处理执行失败和自修复。
- 你是否能结合指标平台口径。

### 4.2 推荐架构

```text
User Question
  |
  v
Query Rewrite
  |
  v
Schema Retrieval
  |-- BM25
  |-- Vector
  |-- Rerank
  v
SQL Generation
  |
  v
SQL Validation
  |-- Parser / AST
  |-- Permission Check
  |-- Tenant Policy
  |-- Limit Injection
  |-- Explain Cost Guard
  v
SQL Sandbox Execution
  |
  v
Self Reflection / Repair
  |
  v
Result Summarization
```

### 4.3 Query Rewrite

目标：

- 消除口语化。
- 补全时间范围。
- 抽取指标、维度、过滤条件。
- 识别业务口径。
- 生成检索 query。

输出结构：

```json
{
  "intent": "rank customers by spend",
  "metric": "cost",
  "dimensions": ["customer"],
  "filters": ["region = Shanghai"],
  "time_range": "last month",
  "limit": 10
}
```

Agent 场景：

> Query Rewrite 不是为了美化问题，而是为了让后续 Schema Retrieval 和 SQL Generation 更稳定。

### 4.4 Schema Retrieval

检索内容：

```text
table schema
column comments
metric definitions
join graph
partition columns
sample values
business glossary
historical SQL
```

召回架构：

```text
Query
  -> BM25 Top 50
  -> Vector Top 50
  -> Merge / Dedup
  -> Rerank Top 10
  -> Build Schema Context
```

高分点：

> 只把相关 schema 放进 prompt，既降低 token 成本，也降低模型 hallucination。并且 schema context 要带权限过滤，用户没权限的表不进入候选。

### 4.5 SQL Generation

Prompt 输入：

```text
rewritten_query
schema_context
join_paths
metric_definitions
database dialect
security rules
output JSON schema
```

输出：

```json
{
  "sql": "select ...",
  "tables": ["orders", "customers"],
  "columns": ["amount", "customer_id"],
  "assumptions": ["last month means calendar month before current month"]
}
```

禁止：

- 使用未提供 schema。
- 生成 DDL/DML。
- 省略 tenant/filter。
- 无 limit 查询明细。

### 4.6 SQL Validation

Validation 分层：

```text
Syntax:
  SQL Parser / EXPLAIN

Safety:
  only SELECT / WITH
  block DDL/DML
  reject multi-statement
  reject dangerous functions

Permission:
  table/column auth
  row-level policy
  tenant isolation

Performance:
  limit injection
  statement timeout
  explain rows threshold
  partition condition check

Semantic:
  table/column exists
  join path valid
  metric definition matched
```

AST 例子：

```text
SQL text
  -> Parser
  -> AST
  -> visit Select
  -> collect tables/columns
  -> validate policies
  -> rewrite limit/tenant filters
```

### 4.7 SQL Sandbox

Sandbox 不是只读校验一个点，而是一组防线：

```text
只读账号
只读事务
SQL Parser
多语句拦截
DDL/DML 黑名单
租户条件注入
Limit 注入
statement_timeout
resource group
审计日志
```

### 4.8 执行

执行链路：

```text
Validated SQL
  -> Query Gateway
  -> Routing
  -> DB / OLAP Engine
  -> Result Fetch
  -> Result Compress
  -> Audit
```

返回结构：

```json
{
  "columns": ["name", "age", "city"],
  "rows": [],
  "row_count": 5,
  "execution_time_ms": 37,
  "query_id": "q_123"
}
```

### 4.9 Self Reflection

基于执行反馈：

```text
error:
  relation not found
  column not found
  syntax error
  timeout
  permission denied

result quality:
  empty result
  too many rows
  wrong columns
```

策略：

```text
permission denied:
  不修复绕过，直接说明权限不足

column not found:
  重新检索 schema，生成候选字段

empty result:
  检查过滤条件和时间范围，但不擅自扩大敏感范围

timeout:
  加 limit、聚合、过滤条件，或提示用户缩小范围
```

### 4.10 Result Summarization

输出要忠实于结果：

```text
直接答案
关键数据
时间范围
口径说明
SQL 摘要
不确定性
```

不要：

- 编造结果。
- 把空结果解释成业务结论。
- 隐藏权限失败。
- 不说明过滤条件。

### 4.11 本章高频问题

#### 高频问题

- 如何设计 SQL Agent？
- Schema Retrieval 怎么做？
- SQL Agent 怎么保证安全？
- AST 校验做什么？
- 怎么处理 SQL 执行失败？
- SQL Agent 怎么支持多租户？
- 怎么做 Limit 注入？

#### 面试回答模板

```text
我会把 SQL Agent 设计成检索增强、受控生成、验证执行、反馈修复的闭环。
自然语言先做 Query Rewrite，然后用 BM25 + Vector + Rerank 检索相关 schema 和指标口径。
SQL 生成后不会直接执行，而是进入 SQL Validation，包括 AST 解析、只读校验、权限、多租户、Limit 注入和 Explain cost guard。
执行在只读 sandbox 中完成，失败后基于数据库错误做有限次数 Self Reflection，最后基于真实结果总结输出。
```

#### 高分回答

> 企业 SQL Agent 最大风险不是 SQL 写不出来，而是写错、查错、查越权、查太慢。我的设计重点是把模型生成限制在受控 schema 和权限范围内，通过 AST、Explain、只读账号、租户策略和审计保证安全。执行结果进入反思修复闭环，但权限错误不会自动绕过。

#### 常见错误回答

- 直接 NL2SQL 后执行。
- 不做 schema 权限过滤。
- 不做 limit。
- 不处理空结果。
- 反思无限重试。

#### 常见追问

- 如果用户问“所有客户明细”，但表很大怎么办？
- 如果模型生成跨租户 SQL 怎么拦？
- 指标口径冲突怎么办？
- 如何评测 SQL Agent？

---

## 5. Agent 沙箱与安全

### 5.1 面试官真正想考什么

企业 Agent 的核心风险：

- SQL 越权。
- Tool 滥用。
- Runtime 执行危险代码。
- 网络访问泄漏。
- Memory 泄漏。
- 多租户串数据。
- Prompt injection。

### 5.2 SQL Sandbox

防线：

```text
Parser / AST
只读账号
只读事务
禁止 DDL/DML
禁止多语句
权限校验
租户隔离
Limit 注入
Explain Cost Guard
Timeout
Audit
```

### 5.3 Tool Sandbox

Tool 分级：

```text
Low Risk:
  查询天气、查询公开文档

Medium Risk:
  SQL 查询、指标查询、内部 API

High Risk:
  写数据库、发消息、改配置、创建任务
```

治理：

- Tool Registry。
- JSON Schema 参数校验。
- 用户授权。
- 租户授权。
- 审批流。
- Dry-run。
- Audit log。

### 5.4 Runtime Sandbox

Python Runtime 风险：

- 文件读写。
- 网络访问。
- CPU/内存打满。
- 死循环。
- 依赖冲突。
- 数据泄漏。

设计：

```text
Scheduler
  -> env_hash
  -> venv/container
  -> worker process
  -> resource quota
  -> timeout
  -> network policy
```

不同依赖版本：

```text
env_hash = hash(python_version + requirements)
env_hash -> venv/container
session_id -> worker process -> namespace
```

### 5.5 Network Sandbox

规则：

- 默认禁止外网。
- 内部服务白名单。
- 数据源白名单。
- DNS 限制。
- egress 审计。

### 5.6 Permission Sandbox

权限模型：

```text
User
  -> Role
  -> Tenant
  -> Data Scope
  -> Tool Scope
  -> Row/Column Policy
```

Agent 不能绕过原有权限系统。

### 5.7 State Sandbox

隔离：

```text
conversation_id -> messages
session_id -> runtime namespace
tenant_id -> data scope
user_id -> permissions
```

不要：

- 多用户共享 runtime namespace。
- Memory 不带租户。
- SQL cache 不带权限。

### 5.8 本章高频问题

#### 高频问题

- Agent 怎么做安全？
- SQL Sandbox 怎么设计？
- Python Runtime 怎么隔离？
- Prompt injection 怎么防？
- 多租户怎么隔离？

#### 面试回答模板

```text
我会把 Agent 安全分成 SQL、Tool、Runtime、Network、Permission、State 六层。
SQL 层通过 AST、只读账号、权限、多租户和 limit 控制。
Tool 层通过 Registry、Schema、权限和审计控制。
Runtime 层通过 venv/container、进程隔离、资源限制和网络白名单控制。
State 层保证 conversation、session、memory、cache 都带租户和用户边界。
```

#### 高分回答

> 企业 Agent 的安全不能只靠 prompt。Prompt 可以提醒模型，但真正安全边界必须在执行层。比如 SQL 必须经过 AST 和权限校验，Tool 必须经过 Tool Gateway，Runtime 必须有进程或容器隔离，缓存和 Memory 必须带权限上下文。

#### 常见错误回答

- 在 prompt 里写“不要执行危险 SQL”。
- 用同一个数据库高权限账号。
- 不审计 tool call。
- 多租户共用 Memory。

---

## 6. 系统设计

### 6.1 Agent 平台整体架构

```text
Client / Console / API
  |
  v
Agent Gateway
  - Auth
  - Tenant
  - Rate Limit
  - Request Trace
  |
  v
Agent Orchestrator
  - LangGraph Workflow
  - State Manager
  - Planner / Router
  - Checkpoint
  |
  v
Tool Gateway
  - Tool Registry
  - Permission
  - Audit
  - Timeout / Retry
  |
  +--> SQL Runtime / Query Gateway
  +--> Python Runtime
  +--> Metric Platform
  +--> MCP Tools
  |
  v
Memory Layer
  - Short-term
  - Summary
  - Vector Memory
  - Result Store
  |
  v
Observability
  - Logs
  - Metrics
  - Traces
  - Eval
```

### 6.2 Runtime 架构

```text
Runtime Scheduler
  |
  |-- Env Manager
  |     env_hash -> venv/container
  |
  |-- Session Manager
  |     session_id -> worker
  |
  |-- Worker Pool
  |     process/container
  |
  |-- Result Store
  |     large result -> reference
```

结合经历：

> 我之前做过长生命周期 Worker、Session 绑定和 Runtime 调度，这和 Agent Code Interpreter 很接近。同一个 conversation 绑定 runtime session，可以保留变量；不同 env_hash 隔离依赖；worker 空闲后回收。

### 6.3 Tool Registry

字段：

```text
tool_name
description
json_schema
owner
risk_level
timeout
rate_limit
permission_policy
audit_policy
tenant_scope
fallback
```

Tool 生命周期：

```text
register -> review -> publish -> gray release -> monitor -> rollback
```

### 6.4 Memory 分层

```text
Messages:
  最近 N 轮

Summary:
  历史对话摘要

Structured State:
  last_sql, selected_tables, created_variables

Vector Memory:
  长期偏好、业务文档

Result Store:
  大 SQL 结果、文件、图表
```

### 6.5 Workflow / LangGraph 状态机

Graph 和 DAG：

- Graph 是通用图，可以有环。
- DAG 是有向无环图。
- Agent workflow 经常有循环，比如 validation failed -> repair -> generation。

状态示例：

```python
state = {
    "messages": [],
    "question": "",
    "rewritten_query": "",
    "schema_context": {},
    "sql": "",
    "validation": {},
    "execution_result": {},
    "reflection_count": 0,
    "final_answer": ""
}
```

流程：

```text
rewrite
  -> retrieve_schema
  -> generate_sql
  -> validate_sql
  -> execute_sql
  -> summarize

validate_sql failed
  -> reflect
  -> generate_sql
```

### 6.6 可观测性与 Tracing

Trace 结构：

```text
trace_id
  request
  model_call
  retrieval
  tool_call
  sql_execution
  runtime_execution
  final_answer
```

每个 span：

```text
start_time
end_time
latency
input_size
output_size
token_usage
status
error
tenant
tool_name
```

企业实践：

- PII 脱敏。
- Prompt 不全量落日志。
- Tool 参数按策略脱敏。
- SQL 审计单独存。

### 6.7 灰度发布 / Retry / Fallback

灰度维度：

- tenant。
- user group。
- agent version。
- prompt version。
- model version。
- tool version。

Fallback：

```text
LLM failed -> fallback model
SQL Agent failed -> return SQL draft + ask clarification
retrieval failed -> keyword-only retrieval
Python runtime failed -> retry new worker
tool timeout -> partial answer
```

### 6.8 本章高频问题

#### 高频问题

- 设计一个企业 Agent 平台。
- Tool Registry 怎么设计？
- Memory 怎么分层？
- LangGraph 状态怎么设计？
- Agent 怎么做 tracing？
- 怎么灰度发布一个 Agent？

#### 面试回答模板

```text
我会把平台拆成 Agent Gateway、Orchestrator、Tool Gateway、Runtime、Memory 和 Observability。
Gateway 负责认证、租户和限流；Orchestrator 负责 LangGraph workflow 和状态；Tool Gateway 负责工具注册、权限、审计；Runtime 负责 SQL/Python 执行；Memory 负责上下文和长期记忆；Observability 负责 trace、metrics 和 eval。
```

#### 高分回答

> 企业 Agent 平台的难点是把不确定的模型输出放进确定的工程边界里。模型可以规划和生成，但工具执行、权限、状态、重试、审计、缓存和灰度都要工程系统兜底。

---

## 7. 性能与稳定性

### 7.1 面试官真正想考什么

- Token 成本如何控制。
- Agent 延迟如何优化。
- SQL 查询如何缓存。
- Tool 调用如何并行。
- 超时、限流、熔断、降级如何做。

### 7.2 Token 成本与上下文压缩

策略：

```text
sliding window:
  保留最近 N 轮

summarize:
  旧对话压缩为摘要

structured memory:
  last_sql / variables / selected_schema

result reference:
  大结果不进 prompt，只放 result_id

schema pruning:
  只放 Top-K schema
```

### 7.3 Parallel Tool Calling

适合并行：

```text
BM25 retrieval + Vector retrieval
多个只读 API 查询
多个 schema source 查询
```

不适合并行：

```text
依赖上一步结果的 SQL execution
需要顺序更新状态的 runtime execution
```

### 7.4 SQL Cache

缓存层：

```text
Schema Cache
Retrieval Cache
SQL Generation Cache
SQL Result Cache
Metric Result Cache
```

注意权限：

```text
cache_key = tenant + user_scope + normalized_sql + datasource + policy_version
```

### 7.5 Timeout / 限流 / 熔断 / Retry

Timeout：

```text
model timeout
retrieval timeout
sql timeout
tool timeout
runtime timeout
overall request timeout
```

限流：

```text
tenant
user
tool
model
datasource
```

Retry：

- 幂等工具可重试。
- 写操作不随便重试。
- SQL timeout 不应盲目重试同一 SQL。

熔断：

- 模型异常率高。
- 数据源慢查询。
- Runtime worker 大量失败。

Fallback：

- 小模型降级。
- 缓存结果。
- 只返回 SQL 草稿。
- 请求用户缩小范围。

### 7.6 Latency 优化

链路拆解：

```text
Total Latency =
  rewrite model
  + retrieval
  + rerank
  + sql generation
  + validation
  + sql execution
  + summarization model
```

优化：

- 合并模型调用。
- 并行 retrieval。
- 缓存 schema context。
- 减少 rerank topK。
- SQL 结果采样。
- 流式输出。

### 7.7 本章高频问题

#### 高频问题

- Agent 延迟太高怎么优化？
- Token 成本怎么降？
- 上下文怎么裁剪？
- Tool 调用失败怎么降级？
- SQL Cache 怎么设计？

#### 面试回答模板

```text
我会先拆链路看耗时：模型、检索、rerank、SQL、工具和总结分别耗时多少。
优化上先做上下文压缩和 schema pruning，再做检索并行和缓存。
稳定性上每个外部依赖都要有 timeout、限流、熔断和 fallback。
SQL 结果不能无限进入 prompt，要做 sample、summary 和 result reference。
```

#### 高分回答

> Agent 性能优化不能只看模型速度。企业 SQL Agent 里，schema retrieval、rerank、SQL execution 和 result summarization 都可能成为瓶颈。我的做法是链路 tracing 后分段优化，同时用上下文压缩、缓存、并行工具、timeout 和 fallback 控制成本和稳定性。

---

## 8. 技术攻关与项目包装

### 8.1 如何包装 Flight SQL

不要只说：

> 我做过 Flight SQL Proxy。

要说：

> Flight SQL Proxy 本质上是高性能数据访问网关，解决多语言客户端和后端数据源之间的统一访问、认证、路由和结果传输问题。放到 Agent 场景里，它可以作为 SQL Tool Runtime 的底层通道，为 Agent 提供标准化、高性能、可审计的数据查询能力。

映射：

```text
Flight SQL Proxy
  -> Agent SQL Tool Gateway

Arrow columnar result
  -> 高效传输 SQL result / DataFrame

ADBC
  -> 多语言 Agent Tool Client
```

### 8.2 OAuth2

包装：

> OAuth2 接入经验可以迁移到 Agent 平台的用户身份和工具授权。Agent 调用工具时必须带用户身份、租户和 scope，不能用平台超级账号代替用户访问数据。

链路：

```text
User Token
  -> Agent Gateway
  -> Tool Gateway
  -> SQL Gateway
  -> Data Source Policy
```

### 8.3 Gateway 高可用

Agent 平台同样需要：

- 多实例。
- 健康检查。
- 流量路由。
- 熔断。
- 限流。
- 灰度。
- 请求追踪。

包装：

> 我做 Gateway 时关注高可用、路由、认证和稳定性，这些能力在企业 Agent 平台里会变成 Agent Gateway 和 Tool Gateway 的核心能力。

### 8.4 Runtime

过去：

```text
Python Runtime
  - 长生命周期 Worker
  - Session 绑定
  - Runtime 调度
```

Agent：

```text
Code Interpreter Runtime
  - conversation -> session
  - env_hash -> execution environment
  - worker process -> namespace
  - timeout / resource limit
```

面试表述：

> 我参考 Ray Scheduler/Worker/Actor 架构思想实现了轻量级 Python Runtime。虽然不是直接基于 Ray 二开，但抽象上包括 Scheduler、Worker、Session、Namespace 和生命周期管理。这可以作为 Agent 的 Code Interpreter 后端。

### 8.5 Query Routing

Agent 场景：

```text
Generated SQL
  -> SQL Gateway
  -> datasource routing
  -> engine routing
  -> tenant routing
  -> read replica / OLAP / cache
```

高分点：

> SQL Agent 不应该直接连数据库，而应该走 Query Gateway。这样可以复用权限、审计、缓存、路由和限流能力。

### 8.6 Session

过去：

```text
JDBC session
runtime session
query session
```

Agent：

```text
conversation_id
  -> langchain/langgraph messages
  -> runtime_session_id
  -> sql history
  -> memory state
```

多轮能力：

```text
每轮用户输入 append 到 messages
复用同一个 runtime_session_id
保留变量 namespace
```

### 8.7 TLS / ADBC

TLS：

- 数据传输加密。
- 内部服务互信。
- Agent Tool 调用安全。

ADBC：

- 标准化数据访问。
- 多语言客户端。
- Agent runtime 可以通过统一协议访问数据。

### 8.8 本章高频问题

#### 高频问题

- 你过去的 Gateway 经验和 Agent 有什么关系？
- Flight SQL 怎么和 AI Agent 结合？
- OAuth2 在 Agent 平台里怎么用？
- Runtime 怎么支持多租户和多版本依赖？
- Query Routing 如何服务 SQL Agent？

#### 面试回答模板

```text
我过去做的不是业务 CRUD，而是数据平台基础设施。
这些能力和 Agent 平台非常接近：Agent 需要 Tool Gateway、SQL Gateway、Runtime、Session、权限、审计、路由和缓存。
比如 Flight SQL 可以作为 SQL Tool 的高性能查询通道；OAuth2 可以做用户级授权；Runtime 可以做 Code Interpreter；Query Routing 可以保证 SQL Agent 生成的查询走正确数据源并受到治理。
```

---

## 9. 高频面试题

### 9.1 Java / JVM

#### Q1：JVM Full GC 怎么排查？

面试回答模板：

```text
我会先看 GC log 和监控，确认 Full GC 频率、Old 区变化、停顿时间和触发原因。
然后通过 heap dump 或 jmap histogram 找大对象和引用链。
在 Agent 平台里，我会重点排查 messages、tool result、SQL result、memory cache 和 trace buffer 是否无限增长。
修复上优先控制业务对象生命周期，例如上下文裁剪、大结果外部化、缓存 TTL，再考虑 JVM 参数。
```

高分回答：

> 如果是 Flight SQL 或 Arrow 相关服务，我还会看 Direct Memory，因为列式数据和 Netty 可能使用堆外内存。

常见错误：

> 直接调大堆。

追问：

- 怎么判断是内存泄漏还是流量导致？
- Heap dump 怎么看？

### 9.2 Spring / MyBatis

#### Q2：Spring AOP 在 Agent 平台有什么用？

模板：

```text
AOP 适合做横切治理，比如 Tool 权限、审计、Tracing、限流和租户校验。
但核心执行链路我不会完全藏在 AOP 里，而是设计 Tool Gateway 显式承载这些逻辑，AOP 可以作为补充。
```

高分：

> Agent 平台每次工具调用都要记录 trace、检查权限、统计 token 和工具成本，这些都可以抽象成统一拦截机制。

### 9.3 数据库

#### Q3：SQL 慢查询怎么优化？

模板：

```text
先用 explain 看执行计划，包括访问类型、索引、扫描行数、Extra。
再结合业务语义看 where、join、order by、limit、索引设计和数据分布。
优化包括补索引、改写 SQL、覆盖索引、减少回表、避免隐式转换和函数、控制扫描范围。
在 SQL Agent 里，生成后还要做 explain cost guard，避免模型生成慢 SQL。
```

常见追问：

- Using filesort 一定不好吗？
- 覆盖索引为什么快？
- 大表分页怎么优化？

### 9.4 SQL Agent

#### Q4：如何设计一个 SQL Agent？

模板：

```text
我会设计成 Query Rewrite、Schema Retrieval、SQL Generation、SQL Validation、Execution、Self Reflection、Summary 的闭环。
Schema Retrieval 用 BM25 + Vector + Rerank，减少 schema hallucination。
SQL 生成后必须经过 AST、安全、权限、多租户、limit 和 explain 校验。
执行在只读 sandbox 中完成，失败后基于错误做有限次数修复。
最终回答基于真实查询结果总结。
```

高分：

> SQL Agent 的核心是受控执行，不是生成 SQL。企业系统必须保证安全、权限、成本和可观测。

错误回答：

> 直接把用户问题发给大模型，让它生成 SQL 后执行。

### 9.5 Agent 工程

#### Q5：LangChain 和 LangGraph 区别？

模板：

```text
LangChain 是高层 Agent 开发框架，适合快速做 tool-calling MVP。
LangGraph 是状态机/图编排框架，适合复杂 workflow、多 Agent、循环、checkpoint 和 human-in-the-loop。
SQL Agent 这种有生成、校验、执行、反思循环的流程，我更倾向用 LangGraph 显式控制。
```

### 9.6 Memory

#### Q6：Agent Memory 怎么设计？

模板：

```text
Memory 要分层。短期 memory 是最近 messages，working memory 是当前任务状态，比如 last_sql、selected_schema、runtime variables，长期 memory 是用户偏好、指标口径和历史查询。
大结果不直接放 prompt，而是放 result store，messages 里只放摘要和引用。
所有 memory 都要带 tenant/user 权限边界和 TTL。
```

### 9.7 Runtime

#### Q7：如何支持不同 Python 版本和依赖？

模板：

```text
用户提交 code 时带 python_version 和 requirements。Scheduler 规范化后计算 env_hash。
env_hash 对应 venv/container 环境，相同依赖复用同一环境。
每个 session 使用该环境里的 Python 启动独立 worker process，session 绑定 worker，namespace 隔离。
venv 解决磁盘依赖隔离，独立进程解决运行时 import 隔离。
```

高分：

> env_hash 不包含 session_id，否则无法复用环境。session 引用 env_hash，但不同 session 有不同 worker 和 namespace。

### 9.8 Gateway

#### Q8：你的 Gateway 背景怎么迁移到 Agent？

模板：

```text
Gateway 经验可以迁移到 Agent Gateway 和 Tool Gateway。
过去我做认证、路由、协议转换、SQL 执行链路和高可用；Agent 平台同样需要认证、租户、工具路由、权限、审计、限流、熔断和可观测。
特别是 SQL Agent，最终 SQL 不应该直连数据库，而应走 Query Gateway 复用治理能力。
```

### 9.9 多轮对话

#### Q9：Agent 怎么支持多轮对话？

模板：

```text
多轮需要保留两类状态：LLM messages 和 runtime session。
每轮用户输入 append 到 messages，调用后用 result["messages"] 作为下一轮上下文。
同时 conversation_id 绑定 runtime_session_id，这样 Python/SQL 上下文可以复用。
上下文不能无限增长，需要 sliding window、summary、structured state 和 result reference。
```

### 9.10 Human-in-the-loop

#### Q10：Human-in-the-loop 是 LangChain 还是 LangGraph？

模板：

```text
两边都有，高层可以用 LangChain middleware，底层能力更偏 LangGraph interrupt/checkpoint/resume。
复杂 SQL 审批或高危工具调用，我会在 LangGraph 节点里显式 interrupt，等待人工 approve/edit/reject，再 resume。
```

---

## 10. 面试总结

### 10.1 如何把数据库 / Gateway 背景转成 Agent 工程背景

核心映射：

```text
Query Gateway
  -> Tool Gateway / SQL Tool Gateway

Flight SQL Proxy
  -> Agent 数据查询运行时

OAuth2
  -> Agent 用户授权 / Tool 权限

Session 管理
  -> Conversation Session / Runtime Session

Query Routing
  -> SQL Routing / Tool Routing / Model Routing

SQL Cache
  -> Agent Result Cache / SQL Cache

Runtime 调度
  -> Code Interpreter / Sandbox Runtime

TLS / ADBC
  -> 企业安全通信 / 多语言数据访问工具
```

推荐表达：

> 我过去的经验集中在数据访问、查询链路、运行时和网关层。Agent 平台落地时，真正难点也是这些工程能力：如何让模型安全访问数据，如何治理 Tool，如何做 Runtime 隔离，如何保证多租户权限，如何做 Trace 和评测。因此我不是从零转 Agent，而是把已有数据平台基础设施经验迁移到 Agent 工程化。

### 10.2 如何避免被问崩

不要夸大：

- 不要说“基于 Ray 二开”，如果只是参考 Ray 架构。
- 不要说“精通所有 Agent 框架”，要说理解 Harness 共性。
- 不要说“SQL Agent 准确率 100%”。
- 不要说“靠 prompt 保证安全”。

可以这样回答不确定问题：

```text
这个框架具体 API 我可能还需要查文档，但从工程抽象上看，它应该包含 model、tool、memory、state 和 trace 几部分。
我会先保证架构边界正确，再补具体实现细节。
```

### 10.3 如何突出系统能力

回答要多用：

- 分层架构。
- 请求链路。
- 状态流转。
- 失败处理。
- 权限边界。
- 可观测性。
- Tradeoff。

比如：

```text
我会先把系统拆成 Agent 编排层、Tool Runtime 层、数据治理层和可观测层。
然后说明每层职责、关键数据结构、失败处理和扩展点。
```

### 10.4 如何体现工程化能力

关键词：

```text
权限
多租户
审计
限流
熔断
超时
重试
缓存
灰度
回滚
trace
eval
成本
安全
```

面试中主动补：

> Demo 可以只跑通链路，但企业 Agent 要考虑 Tool Governance、Memory Governance、SQL Sandbox、Runtime Sandbox、Tracing、Evaluation 和成本控制。

### 10.5 如何体现 AI 学习能力

你可以说：

> 我最近系统学习了 LangChain、LangGraph、MCP、Memory、RAG、BM25 + Vector + Rerank、SQL Agent、Self Reflection 和 Multi-Agent。我也基于自己的 Runtime 做了 LangChain + DeepSeek 的 MVP，把 Runtime 封装成 execute_python/get_variable 工具，并扩展了 PostgreSQL execute_sql 工具，验证 Agent 调用自研 Runtime 和数据库工具的闭环。

这个回答比“我看过 LangChain”更有说服力，因为它有工程落点。

### 10.6 最终面试自我介绍模板

```text
我主要是 Java 后端和数据平台基础设施方向，过去做过数据库连接层、Query Gateway、Flight SQL Proxy、ADBC、OAuth2、Query Routing、SQL Cache、Session 管理和 Runtime 调度。

我不是传统纯 CRUD 背景，更多是在数据访问、执行链路和平台基础设施上做工程化。
最近我在把这些经验迁移到 AI Agent 方向，重点关注 SQL Agent、Agent Runtime、Tool Calling、Memory、RAG 和企业 Agent 平台治理。

我理解企业 Agent 的核心不是简单调用大模型，而是让模型在受控边界内访问数据和工具。
所以我会关注 SQL Sandbox、Tool Gateway、权限、多租户、审计、Tracing、评测和 Runtime 隔离。

结合我的经历，Query Gateway 可以演进成 Tool Gateway，Flight SQL 可以成为 SQL Tool Runtime，OAuth2 可以承载 Agent 工具授权，Runtime 调度可以支撑 Code Interpreter。
这是我和普通 Java CRUD 或单纯 Prompt Agent 候选人的差异。
```

### 10.7 最后一页复习口诀

```text
Java:
  JVM、GC、OOM、Spring、MyBatis、Tomcat，必须落到线上排查。

SQL:
  索引、MVCC、Explain、优化、Redis、HBase，必须落到 SQL Agent 安全执行。

Agent:
  Harness、Tool、Memory、Workflow、RAG、Reflection、Eval，必须落到企业治理。

SQL Agent:
  Rewrite、Retrieval、Generation、Validation、Execution、Reflection、Summary。

安全:
  SQL Sandbox、Tool Sandbox、Runtime Sandbox、Network、Permission、State。

系统:
  Gateway、Orchestrator、Tool Registry、Runtime、Memory、Observability。

包装:
  Gateway 背景不是劣势，是企业 Agent 平台基础设施优势。
```

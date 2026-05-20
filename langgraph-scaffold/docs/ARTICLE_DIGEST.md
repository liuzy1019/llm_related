# 《LangGraph 实战指南：从入门到生产级 AI Agent 开发》文章整理

> 原文链接：<https://km.woa.com/articles/show/656075?jumpfrom=kmmcp>
> 作者：luiszhu｜来源：KM · 数立方｜创建：2026-03-30
> 阅读：1629 · 点赞：28 · 收藏：111 · 评论：4 · KM 推荐 / KM 头条
>
> 本文档为原文的精炼整理，配套本仓库脚手架代码 `langgraph-scaffold/`（即第六章「脚手架工程」的可复现实现）。

---

## 0. 这篇文章解决什么问题？

构建**生产级 AI Agent** 不只是调用 LLM，还要解决：

- 多步循环推理 / 条件分支
- 多轮对话状态 / 跨会话持久化
- 工具调用、人工审核（Human-in-the-Loop）
- 多 Agent 协作 / 流式输出 / 可观测性

**LangGraph** 把 Agent 建模为**有向图（State / Node / Edge）**，统一解决以上问题，已被 Replit、Uber、LinkedIn 等公司用于生产。

## 1. 为什么是 LangGraph？

### 1.1 LLM 应用的四次进化

| 阶段 | 代表方案 | 核心局限 |
| --- | --- | --- |
| 第一代 | 直接调用 OpenAI API | 单轮，无记忆，无工具 |
| 第二代 | LangChain Chain / LCEL | 线性管道，无循环、无条件分支 |
| 第三代 | LangChain Agent | 有循环但状态管理混乱，难生产化 |
| **第四代** | **LangGraph** | ✅ 图结构 + 状态机 + 持久化，生产就绪 |

### 1.2 LangChain 是前置知识，不是竞争对手

LangGraph 是 **LangChain 生态的上层扩展**，底层依赖 `langchain-core`：LCEL、`@tool` 装饰器、`with_structured_output` 等抽象是必须掌握的前置技能。

## 2. 核心原理：图是怎么跑起来的

### 2.1 三大要素

| 要素 | 一句话定义 | 关键点 |
| --- | --- | --- |
| **State** | 全局共享的数据结构（`TypedDict`） | 字段用 `Annotated[..., reducer]` 声明归约函数 |
| **Node** | 执行具体任务的函数 | 接收 state，返回 dict 更新 state |
| **Edge** | 控制节点流转 | 普通边 + 条件边（`add_conditional_edges`） |

> ⚠️ **最容易踩的坑**：消息列表必须用 `add_messages` 作为归约函数，否则每次节点返回都会**覆盖**整个历史。

### 2.2 运行生命周期

`invoke()` → 编译 → 进入入口节点 → 节点执行 → 状态合并（应用 reducer） → 条件路由 → 写 Checkpoint → 下一节点 / END。

## 3. Agent 模式实战

### 3.1 ReAct（最常用）

**Reasoning + Acting**：思考 → 行动 → 观察 的循环。

最简实现（5 行）：

```python
from langgraph.prebuilt import create_react_agent
agent = create_react_agent(llm, tools=[search_weather, calculate])
agent.invoke({"messages": [("human", "北京今天天气怎么样？")]})
```

底层手动构建版见本仓库 [`app/agents/react_agent.py`](../app/agents/react_agent.py)。

### 3.2 Plan & Execute（复杂任务分治）

适合"先规划再执行"的长任务，例如「写一份完整的市场调研报告」。

```text
START → planner → executor ↻ replanner → END
                      │             │
                      └─── (未完成) ─┘
```

LangChain 早期内置 `plan_and_execute`，**当前版本已移除**，官方推荐自行实现。本仓库见 [`app/agents/plan_execute_agent.py`](../app/agents/plan_execute_agent.py)。

### 3.3 持久化与 Human-in-the-Loop

```python
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "user_001"}}
graph.invoke({"messages": [("human", "我叫张三")]}, config=config)
# 第二轮自动恢复上下文
graph.invoke({"messages": [("human", "我叫什么名字？")]}, config=config)
```

HITL 通过 `interrupt()` + `interrupt_before=[...]` 在敏感节点（如删数据）前暂停，等待人工 `Command(resume=...)` 后继续。

### 3.4 高级特性

- **子图（Subgraph）**：将复杂逻辑封装为可复用模块，`add_node("research", research_subgraph)`
- **流式输出**：`astream_events(..., version="v2")` 流式 token / `stream(..., stream_mode="updates")` 节点级进度

## 4. 生态全景

### 4.1 LangSmith 可观测性

> 一句话：LangSmith 之于 LangGraph，就像 Prometheus+Grafana 之于微服务。

接入零代码侵入，只要 3 行环境变量：

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_xxx
LANGCHAIN_PROJECT=my-agent
```

### 4.2 框架横向对比（节选）

| 框架 | 灵活性 | 状态管理 | 生产就绪 | 适用 |
| --- | --- | --- | --- | --- |
| **LangGraph** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 复杂、有循环、需持久化的 Agent |
| AutoGen | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 多 Agent 对话研究 |
| CrewAI | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | 角色协作型任务 |
| Dify | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | 低代码 / 业务搭建 |

## 5. 生产落地：避坑 + 最佳实践

### 5.1 高频踩坑

| 坑 | 后果 | 解法 |
| --- | --- | --- |
| 消息列表没用 `add_messages` | 历史被覆盖 | `messages: Annotated[list, add_messages]` |
| 没有终止条件 | Agent 无限循环，Token 爆炸 | 加 `iteration_count` 字段 + 上限 |
| 工具抛异常 | 整张图崩溃 | 工具内部 `try/except`，返回错误描述 |
| 生产用 MemorySaver | 重启状态丢失 | 改 `PostgresSaver` |

### 5.2 性能优化

- 异步节点：`async def + await llm.ainvoke(...)`
- Fan-out 并行：多个 `add_edge("start", "task_x")` 并行
- 消息裁剪：`trim_messages(..., max_tokens=4000, strategy="last")`

### 5.3 安全加固清单

| 风险 | 防范 |
| --- | --- |
| Prompt 注入 | 输入过滤 + 系统提示词加固 |
| 工具权限滥用 | 工具白名单 + HITL 审核 |
| 敏感数据泄露 | 数据脱敏 + 私有化部署 |
| 费用失控 | 最大迭代次数 + Token 预算 |
| 幻觉传播 | 关键步骤加验证节点 |

### 5.4 生产 Checklist（精简）

- ✅ State：TypedDict + `add_messages` + iteration_count
- ✅ Node：单一职责、捕获异常、耗时操作 async
- ✅ Checkpointer：开发 Memory / 测试 Sqlite / 生产 Postgres；`thread_id = user_{uid}_session_{sid}`
- ✅ 可观测：LangSmith + 关键节点日志 + Token 告警
- ✅ 测试：节点单测 + 图集成测试 + LangSmith Dataset 回归

## 6. 🚀 第六章：脚手架工程（本仓库对应实现）

> 原文给出推荐目录结构与 5 分钟启动脚本，本仓库 `langgraph-scaffold/` 即按此结构 1:1 落地，并补全了文章里"链接待补充"的实际代码。

### 6.1 推荐项目结构

```
langgraph-scaffold/
├── README.md
├── requirements.txt
├── .env.example                  # 环境变量模板
│
├── app/
│   ├── agents/
│   │   ├── react_agent.py        # ReAct Agent 示例
│   │   ├── plan_execute_agent.py # Plan & Execute 示例
│   │   └── multi_agent.py        # 多 Agent 协作示例
│   ├── tools/
│   │   ├── search_tools.py       # 搜索类工具
│   │   ├── code_tools.py         # 代码执行工具
│   │   └── data_tools.py         # 数据查询工具
│   ├── state/
│   │   └── schemas.py            # 所有 State TypedDict 定义
│   └── checkpointers/
│       └── setup.py              # Checkpointer 工厂函数
│
├── tests/
│   ├── test_nodes.py             # 节点单元测试
│   └── test_graphs.py            # 图集成测试
│
└── scripts/
    └── run_agent.py              # 快速运行入口
```

### 6.2 5 分钟快速启动

```bash
git clone <your-fork>          # 或者直接使用本目录
cd langgraph-scaffold

pip install -r requirements.txt
cp .env.example .env            # 编辑后填入 OPENAI_API_KEY 与 LANGCHAIN_API_KEY

python scripts/run_agent.py --mode react --query "北京今天天气怎么样？"
```

### 6.3 本仓库相比原文的增强

| 维度 | 原文 | 本仓库 |
| --- | --- | --- |
| 离线可跑 | 需要 OpenAI Key | 内置 `MOCK_LLM=1` 模式，零依赖跑通 |
| 计算工具 | `eval(expression)`（不安全） | AST 安全求值版 |
| Checkpointer | 列出三种 | 工厂统一切换 `memory/sqlite/postgres` |
| 多 Agent | 文中未给完整代码 | 给出 Supervisor 模式可运行实现 |
| 测试 | Checklist 提到 | 实际提供 pytest 用例 |

## 7. 总结

> 一句话：**生产环境构建需要多步推理、工具调用、状态管理、人机协作的 AI Agent，LangGraph 是目前 Python 生态中最成熟、最灵活的选择。**

不需要 LangGraph 的场景：

- 简单单轮问答
- 纯 RAG 检索
- 不需要循环的线性流程
  → 直接用 LangChain LCEL 即可，**不要过度设计**。

📌 版本说明：原文基于 LangGraph 0.2.x；框架迭代较快，跑通后建议结合官方文档同步最新 API。

## 参考资料

- 📰 KM 原文：<https://km.woa.com/articles/show/656075?jumpfrom=kmmcp>
- 📚 官方文档：<https://langchain-ai.github.io/langgraph/>
- 🎓 LangGraph Academy：<https://academy.langchain.com/>
- 🛠️ GitHub 示例：<https://github.com/langchain-ai/langgraph>
- 📊 LangSmith 文档：<https://docs.smith.langchain.com/>

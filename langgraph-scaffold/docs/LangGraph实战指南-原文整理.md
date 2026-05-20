# LangGraph 实战指南：从入门到生产级 AI Agent 开发

> **原文链接**：<https://km.woa.com/articles/show/656075?jumpfrom=kmmcp>
> **作者**：luiszhu　|　**来源**：KM · 数立方　|　**创建**：2026-03-30　|　**更新**：2026-04-08
> **统计**：阅读 1629 · 点赞 28 · 收藏 111 · 评论 4 · KM 推荐 / KM 头条 · 热度 53
> **标签**：`agent` · `AI` · `LangGraph`
> **K 吧 / 文集**：[#52874 数立方](https://km.woa.com/group/52874?jumpfrom=kmmcp) · [#9625 数立方](https://km.woa.com/knowledge/9625?jumpfrom=kmmcp) · [#10641 AI Agent 学习实践](https://km.woa.com/knowledge/10641?jumpfrom=kmmcp)
> **附件**：`langgraph-fastapi-multi-agent-main.zip`
>
> 本文档由 KM MCP 拉取原文整理为结构化 Markdown，正文文字与代码均忠实于原文；为可读性所做的调整：
> 1. 章节按层级补齐 Markdown 标题；
> 2. 散落代码片段统一收敛为代码围栏（按 Python / Bash / Text 等标注语言）；
> 3. 原文中的表格还原为 Markdown 表格；
> 4. 原文中标记为 `[图片]` 的位置保留占位说明。

---

## 🎁 读完你能获得

- **底层逻辑**：彻底搞懂 State、Node、Edge 的运行机制与归约原理
- **实战代码**：ReAct、Plan & Execute、子图等主流模式的完整实现
- **生产经验**：持久化配置、LangSmith 监控接入与高频踩坑指南
- **开箱即用**：一套包含完整目录结构与测试用例的工程脚手架

LangGraph 是基于图结构的开源框架，用于构建有状态、可循环、支持多智能体协作与人工干预的复杂 AI 工作流。

> 👉 [LangGraph 官网](https://langchain-ai.github.io/langgraph/) ｜ *[图片：LangGraph 架构图]*
>
> 下面逐步揭开她的面纱。

---

## 一、为什么是 LangGraph？先搞清楚背景

### 1.1 LLM 应用的三次进化

很多同学上来就问"LangGraph 怎么用"，但如果不理解它解决了什么问题，学起来会很痛苦。先看这张演进图：

> *[图片：LLM 应用四代演进示意]*

| 阶段 | 代表方案 | 核心局限 |
| --- | --- | --- |
| 第一代 | 直接调用 OpenAI API | 单轮，无记忆，无工具 |
| 第二代 | LangChain Chain / LCEL | 线性管道，无法循环，无法条件分支 |
| 第三代 | LangChain Agent | 有循环但状态管理混乱，难以生产化 |
| **第四代** | **LangGraph** | ✅ 图结构 + 状态机 + 持久化，生产就绪 |

### 1.2 LangChain 是前置知识，不是竞争对手

**常见误区**：很多人以为 LangGraph 是 LangChain 的替代品。错！LangGraph 是 LangChain 生态的上层扩展，底层依赖 `langchain-core` 的所有基础抽象。

> *[图片：LangChain 与 LangGraph 关系图]*

LangChain 核心抽象速览（必须掌握）：

```python
# ① LCEL 管道操作符：最常用的链式调用方式
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="gpt-4o", temperature=0)

# prompt | llm | parser 就是一条 Chain
chain = (
    ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的代码助手"),
        ("human", "{question}")
    ])
    | llm
    | StrOutputParser()
)

result = chain.invoke({"question": "什么是递归？"})

# ② Tool 装饰器：定义 Agent 可调用的工具
from langchain_core.tools import tool

@tool
def search_web(query: str) -> str:
    """搜索互联网，返回相关信息"""  # docstring 会成为工具描述，LLM 靠它决定何时调用
    return f"关于 '{query}' 的搜索结果..."
```

LangChain 的根本局限——**Chain 是线性的，无法表达 Agent 需要的循环逻辑**：

> *[图片：线性 Chain 与循环 Agent 对比]*

这就是 LangGraph 诞生的原因：**用图结构打破线性限制**。

### 1.3 LangGraph 的核心价值，一张图说清楚

> *[图片：LangGraph 核心价值全景图]*

---

## 二、核心原理：图是怎么跑起来的

### 2.1 安装与包依赖

> 💡 **先装对包，避免版本冲突是第一道坑。**

**最小化安装（推荐新手从这里开始）**：

```bash
# 核心：LangGraph + OpenAI 模型
pip install langgraph langchain-openai

# 本地开发持久化（SQLite，零配置）
pip install langgraph-checkpoint-sqlite

# 可观测性（强烈推荐，零代码侵入）
pip install langsmith
```

**生产环境完整安装**：

```bash
pip install \
    langgraph \
    langchain-core \
    langchain-openai \
    langchain-community \
    langsmith \
    langgraph-checkpoint-postgres \
    psycopg[binary] \
    python-dotenv \
    pydantic
```

**`requirements.txt` 版本锁定**（截至 2025 年稳定版）：

```text
# ===== 核心（必须）=====
langgraph>=0.2.0,<0.3.0
langchain-core>=0.3.0,<0.4.0

# ===== 模型接入（按需选一个）=====
langchain-openai>=0.2.0       # OpenAI / Azure
langchain-anthropic>=0.2.0    # Claude
langchain-google-genai>=2.0.0 # Gemini
langchain-ollama>=0.2.0       # 本地模型

# ===== 工具扩展（可选）=====
langchain>=0.3.0
langchain-community>=0.3.0

# ===== 持久化（二选一）=====
langgraph-checkpoint-sqlite>=2.0.0    # 本地开发
langgraph-checkpoint-postgres>=2.0.0  # 生产环境
psycopg[binary]>=3.1.0                # postgres 驱动

# ===== 运维与工具 =====
langsmith>=0.1.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

**各包职责一览**：

| 包名 | 必须？ | 职责 |
| --- | :---: | --- |
| `langgraph` | ✅ | 图构建、节点/边/状态、编译运行 |
| `langchain-core` | ✅ | Message、Tool、Runnable 基础抽象 |
| `langchain-openai` | 按需 | OpenAI / Azure 模型接入 |
| `langchain-anthropic` | 按需 | Claude 系列模型 |
| `langchain-ollama` | 按需 | 本地 Ollama 模型 |
| `langchain-community` | 可选 | 社区工具、向量库等 |
| `langgraph-checkpoint-sqlite` | 可选 | SQLite 持久化，本地开发首选 |
| `langgraph-checkpoint-postgres` | 可选 | PostgreSQL 持久化，生产首选 |
| `langsmith` | 推荐 | 全链路追踪、评估、监控 |

**环境变量配置**（`.env` 文件）：

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# LangSmith（只需这三行，自动开启全链路追踪）
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=my-langgraph-project

# 国内代理（如需）
# OPENAI_BASE_URL=https://your-proxy.com/v1
```

```python
from dotenv import load_dotenv
load_dotenv()  # 加载 .env，放在入口文件最顶部
```

### 2.2 三大核心要素：State、Node、Edge

LangGraph 的一切都围绕这三个概念展开，理解它们是掌握框架的关键：

> *[图片：State / Node / Edge 三要素关系图]*

#### ① State：用 TypedDict 定义，支持归约函数

```python
from typing import TypedDict, Annotated, List
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # ⭐ 关键：add_messages 是归约函数，表示"追加"而非"覆盖"
    # 没有它，每次节点返回都会把历史消息清空！
    messages: Annotated[List[BaseMessage], add_messages]

    # 普通字段：直接覆盖（最新值生效）
    final_answer: str
    iteration_count: int  # 用于防止无限循环
```

> ⚠️ **归约函数（Reducer）是 LangGraph 最容易踩坑的地方**：消息列表必须用 `add_messages`，否则每次节点执行都会把历史消息清空！

#### ② Node：普通 Python 函数，只返回需要更新的字段

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

def call_llm(state: AgentState) -> dict:
    """LLM 调用节点：读取消息历史，调用模型，返回新消息"""
    response = llm.invoke(state["messages"])
    # 只返回需要更新的字段，其他字段保持不变
    return {"messages": [response]}
```

#### ③ Edge：三种类型，灵活控制流转

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(AgentState)
builder.add_node("llm", call_llm)
builder.add_node("tools", tool_executor)

# 类型1：普通边（固定流转）
builder.add_edge(START, "llm")

# 类型2：条件边（动态路由，Agent 的核心）
def should_continue(state: AgentState) -> str:
    """路由函数：有工具调用就去执行工具，否则结束"""
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return END

builder.add_conditional_edges("llm", should_continue)

# 类型3：工具执行完回到 LLM（形成循环）
builder.add_edge("tools", "llm")

graph = builder.compile()
```

生成的图结构：

> *[图片：编译后的状态图拓扑]*

### 2.3 编译原理：`compile()` 做了什么

> *[图片：compile() 内部流程示意]*

### 2.4 运行时原理：一次 `invoke` 的完整生命周期

这是理解 LangGraph 最核心的部分，很多文章都没讲清楚：

> *[图片：invoke 运行时生命周期]*

### 2.5 全链路时序图：一次 ReAct Agent 调用的完整过程

> 这张图是本文最重要的图，建议反复看，直到能默写出来。

> *[图片：ReAct Agent 全链路时序图]*

### 2.6 State 更新机制：归约函数如何工作

> *[图片：reducer 合并示意]*

---

## 三、Agent 模式实战：ReAct、Plan & Execute、子图

### 3.1 ReAct：最主流的 Agent 模式

**ReAct = Reasoning（推理）+ Acting（行动）**，核心思想是让 LLM 在"思考 → 行动 → 观察"的循环中逐步完成任务。

> *[图片：ReAct 循环示意]*

**最简实现（5 行代码）**：

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

llm = ChatOpenAI(model="gpt-4o", temperature=0)

@tool
def search_weather(city: str) -> str:
    """查询指定城市的实时天气"""
    return f"{city}今天晴天，温度15°C，湿度60%"

@tool
def calculate(expression: str) -> str:
    """计算数学表达式，如 '123*456'"""
    try:
        return str(eval(expression))  # 生产环境请用安全的计算库
    except Exception as e:
        return f"计算错误: {e}"

# create_react_agent 内部已经帮你构建好了完整的 ReAct 图
agent = create_react_agent(llm, tools=[search_weather, calculate])

result = agent.invoke({
    "messages": [("human", "北京今天天气怎么样？顺便算一下 123 * 456")]
})
print(result["messages"][-1].content)
```

**手动构建 ReAct（理解底层原理）**：

```python
from typing import Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class ReActState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# 将工具绑定到 LLM（让 LLM 知道有哪些工具可用）
llm_with_tools = llm.bind_tools([search_weather, calculate])

def agent_node(state: ReActState) -> dict:
    """Agent 节点：调用绑定了工具的 LLM"""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def route_after_agent(state: ReActState) -> str:
    """路由函数：有工具调用就去执行，否则结束"""
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return END

builder = StateGraph(ReActState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode([search_weather, calculate]))  # 内置工具执行节点

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route_after_agent)
builder.add_edge("tools", "agent")  # ⭐ 工具执行完回到 agent，形成循环

react_graph = builder.compile()
```

### 3.2 Plan & Execute：复杂任务的分治策略

**适用场景**：任务复杂、步骤多、需要先规划再执行的场景（如：写一份完整的市场调研报告）。

**历史说明**：LangChain 早期内置了 `plan_and_execute` 模块，LangGraph 早期也有官方示例。当前版本已移除内置实现，官方认为 P&E 高度依赖业务场景，推荐自行实现。

> *[图片：Plan & Execute 流程图]*

**核心实现代码**：

```python
from typing import TypedDict, List, Annotated
import operator
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent

# ① 状态定义
class PlanExecuteState(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[tuple], operator.add]  # 追加已完成步骤
    response: str

# ② Planner：输出结构化计划
class Plan(BaseModel):
    steps: List[str] = Field(description="按顺序排列的执行步骤")

planner = (
    ChatPromptTemplate.from_messages([
        ("system", "你是任务规划专家，将目标拆解为具体可执行的步骤"),
        ("human", "目标：{objective}")
    ])
    | llm.with_structured_output(Plan)
)

def plan_step(state: PlanExecuteState) -> dict:
    plan = planner.invoke({"objective": state["input"]})
    return {"plan": plan.steps}

# ③ Executor：执行单个步骤
executor = create_react_agent(llm, tools=[search_weather, calculate])

def execute_step(state: PlanExecuteState) -> dict:
    current_step = state["plan"][0]  # 取第一个未完成步骤
    result = executor.invoke({"messages": [("human", current_step)]})
    return {"past_steps": [(current_step, result["messages"][-1].content)]}

# ④ Replanner：判断是否完成，或更新计划
class Response(BaseModel):
    response: str

class Act(BaseModel):
    action: Plan | Response = Field(description="继续执行新计划 or 给出最终答案")

replanner = (
    ChatPromptTemplate.from_template(
        "目标：{input}\n原计划：{plan}\n已完成：{past_steps}\n"
        "判断：任务完成则给出答案，否则更新剩余计划"
    )
    | llm.with_structured_output(Act)
)

def replan_step(state: PlanExecuteState) -> dict:
    output = replanner.invoke(state)
    if isinstance(output.action, Response):
        return {"response": output.action.response}
    return {"plan": output.action.steps}

def should_end(state: PlanExecuteState) -> str:
    return END if state.get("response") else "executor"

# ⑤ 构建图
pe_builder = StateGraph(PlanExecuteState)
pe_builder.add_node("planner", plan_step)
pe_builder.add_node("executor", execute_step)
pe_builder.add_node("replanner", replan_step)
pe_builder.add_edge(START, "planner")
pe_builder.add_edge("planner", "executor")
pe_builder.add_edge("executor", "replanner")
pe_builder.add_conditional_edges("replanner", should_end)
pe_graph = pe_builder.compile()
```

### 3.3 持久化与 Human-in-the-Loop

**持久化是 LangGraph 的杀手级特性**，三行代码开启：

```python
from langgraph.checkpoint.memory import MemorySaver        # 开发用
from langgraph.checkpoint.sqlite import SqliteSaver        # 本地持久化
# from langgraph.checkpoint.postgres import PostgresSaver  # 生产用

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# thread_id 是会话隔离的关键，不同用户用不同 thread_id
config = {"configurable": {"thread_id": "user_001"}}

# 第一轮对话
graph.invoke({"messages": [("human", "我叫张三")]}, config=config)

# 第二轮对话（自动恢复上下文，Agent 记得"张三"）
result = graph.invoke({"messages": [("human", "我叫什么名字？")]}, config=config)
```

**Human-in-the-Loop：在关键节点等待人工确认**

```python
from langgraph.types import interrupt, Command

def sensitive_delete(state: AgentState) -> dict:
    """敏感操作节点：执行前需要人工确认"""
    # interrupt() 暂停图执行，将 payload 返回给调用方
    approval = interrupt({
        "message": "即将删除数据，是否确认？",
        "target": state["target_data"]
    })

    if approval == "yes":
        return {"result": f"已删除: {state['target_data']}"}
    return {"result": "操作已取消"}

# 编译时声明中断点
graph = builder.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["sensitive_delete"]  # 在此节点前自动中断
)

config = {"configurable": {"thread_id": "task_001"}}

# 第一次调用：运行到中断点自动暂停
graph.invoke(input_data, config=config)

# 人工审核后，传入决策继续执行
graph.invoke(Command(resume="yes"), config=config)
```

**Checkpointer 持久化链路**：

> *[图片：Checkpoint 写入与恢复链路]*

### 3.4 高级特性：子图与流式输出

**子图（Subgraph）**：将复杂逻辑封装为可复用模块

> *[图片：主图嵌套子图]*

```python
# 定义子图（和普通图一样构建，compile 后作为节点使用）
research_builder = StateGraph(ResearchState)
research_builder.add_node("search", search_node)
research_builder.add_node("analyze", analyze_node)
research_builder.add_edge(START, "search")
research_builder.add_edge("search", "analyze")
research_builder.add_edge("analyze", END)
research_subgraph = research_builder.compile()

# 在主图中直接 add_node 子图对象
main_builder = StateGraph(MainState)
main_builder.add_node("research", research_subgraph)  # ⭐ 子图作为节点
main_builder.add_node("write", write_node)
```

**流式输出**：实时展示 LLM 生成过程

```python
# 方式1：流式输出 Token（适合聊天界面）
async for chunk in graph.astream_events(
    {"messages": [("human", "写一首关于春天的诗")]},
    version="v2"
):
    if chunk["event"] == "on_chat_model_stream":
        content = chunk["data"]["chunk"].content
        if content:
            print(content, end="", flush=True)  # 实时打印每个 token

# 方式2：流式输出节点状态（适合进度展示）
for update in graph.stream(
    {"messages": [("human", "分析这段代码")]},
    stream_mode="updates"  # 每个节点完成后输出一次
):
    node_name = list(update.keys())[0]
    print(f"✅ 节点 [{node_name}] 执行完成")
```

---

## 四、生态全景：LangSmith 运维 + 框架横向对比

### 4.1 LangSmith：生产级可观测性平台

> 一句话：**LangSmith 之于 LangGraph，就像 Prometheus + Grafana 之于微服务**。没有它，生产环境的 Agent 就是黑盒。

> *[图片：LangSmith 全链路追踪截图]*

**接入只需 3 行环境变量，零代码侵入**：

```python
import os
# 设置后，所有 LangGraph/LangChain 调用自动上报
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "lsv2_your_key"
os.environ["LANGCHAIN_PROJECT"] = "my-agent-project"

# 之后正常调用，LangSmith 自动记录完整链路
result = graph.invoke({"messages": [("human", "你好")]})
```

**LangSmith Tracing 能看到什么**：

每次 Agent 运行都会生成完整调用树，包括：

- 每个节点的输入 / 输出 State
- LLM 调用的完整 Prompt 和 Response
- 工具调用的参数和返回值
- 每步耗时和 Token 消耗（精确到毫秒）

**自动化评估（CI/CD 集成）**：

```python
from langsmith.evaluation import evaluate

def correctness_evaluator(run, example):
    """用 LLM 评判答案正确性"""
    score = judge_llm.invoke(
        f"问题：{example.inputs['question']}\n"
        f"参考答案：{example.outputs['answer']}\n"
        f"模型答案：{run.outputs['answer']}\n"
        f"评分（0-1）："
    )
    return {"score": float(score.content)}

# 批量评估，自动对比不同版本
results = evaluate(
    graph.invoke,
    data="my-golden-dataset",         # LangSmith 上的数据集名称
    evaluators=[correctness_evaluator],
    experiment_prefix="v2.0-test"     # 实验名称，方便对比
)
```

**生产监控关键指标**：

| 指标 | 说明 | 告警阈值建议 |
| --- | --- | --- |
| P99 延迟 | 99% 请求的响应时间 | `> 30s` 告警 |
| 错误率 | 失败请求占比 | `> 1%` 告警 |
| Token 消耗 / 请求 | 平均 Token 用量 | 突增 50% 告警 |
| 工具调用次数 | 每次 Agent 运行的工具调用轮数 | `> 10` 次告警（可能死循环） |

### 4.2 框架横向对比：选型不踩坑

| 维度 | LangGraph | AutoGen | CrewAI | Dify | Semantic Kernel |
| --- | --- | --- | --- | --- | --- |
| 编程范式 | 图 / 代码优先 | 对话驱动 | 角色扮演 | 低代码可视化 | 代码优先 |
| 学习曲线 | 中等 | 低 | 低 | 很低 | 中等 |
| 灵活性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 状态管理 | ✅ 内置完善 | ⚠️ 基础 | ⚠️ 基础 | ✅ 内置 | ⚠️ 基础 |
| 持久化 | ✅ 原生支持 | ❌ 需自实现 | ❌ 需自实现 | ✅ 内置 | ⚠️ 部分 |
| Human-in-Loop | ✅ 原生支持 | ⚠️ 有限 | ❌ | ✅ 支持 | ⚠️ 有限 |
| 多 Agent | ✅ 原生支持 | ✅ 核心特性 | ✅ 核心特性 | ✅ 支持 | ⚠️ 有限 |
| 可观测性 | ✅ LangSmith | ⚠️ 基础日志 | ⚠️ 基础日志 | ✅ 内置 | ⚠️ 基础 |
| 生产就绪度 | ✅ 高 | ⚠️ 中 | ⚠️ 中 | ✅ 高 | ✅ 高 |
| 社区活跃度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

**选型决策树**：

> *[图片：选型决策树]*

### 4.3 适用场景分析

| 场景 | 适配度 | 核心原因 |
| --- | --- | --- |
| 简单单轮问答 | ⭐⭐ | 杀鸡用牛刀，直接调 LLM 即可 |
| 多轮对话 | ⭐⭐⭐⭐ | 状态管理 + 持久化天然支持 |
| 工具调用 Agent | ⭐⭐⭐⭐⭐ | 核心强项，ReAct 开箱即用 |
| 多 Agent 协作 | ⭐⭐⭐⭐⭐ | 图结构天然表达多 Agent 关系 |
| 长流程自动化 | ⭐⭐⭐⭐⭐ | 持久化 + 断点续传 |
| 需要人工审核 | ⭐⭐⭐⭐⭐ | Human-in-Loop 原生支持 |
| 实时流式应用 | ⭐⭐⭐⭐ | 流式输出支持完善 |

---

## 五、生产落地：避坑指南 + 最佳实践 + 脚手架工程

### 5.1 ⚠️ 高频踩坑：这些错误 90% 的人都犯过

#### 坑 1：消息列表没用 `add_messages`，历史被覆盖

```python
# ❌ 错误：每次节点返回都会覆盖整个 messages 列表
class BadState(TypedDict):
    messages: list  # 没有归约函数！

# ✅ 正确：add_messages 确保消息追加而非覆盖
class GoodState(TypedDict):
    messages: Annotated[list, add_messages]
```

#### 坑 2：没有终止条件，Agent 无限循环

```python
# ❌ 危险：LLM 一直调用工具，Token 费用爆炸
def agent_node(state):
    return {"messages": [llm.invoke(state["messages"])]}

# ✅ 安全：加入迭代计数器，超限强制终止
def safe_agent_node(state: AgentState) -> dict:
    if state.get("iteration_count", 0) >= 10:
        return {"messages": [AIMessage(content="已达最大迭代次数，请简化问题")]}
    response = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [response],
        "iteration_count": state.get("iteration_count", 0) + 1
    }
```

#### 坑 3：工具函数抛异常，导致整个 Agent 崩溃

```python
# ❌ 危险：异常会中断整个图的执行
@tool
def risky_api_call(query: str) -> str:
    return requests.get(f"https://api.example.com/{query}").json()["result"]

# ✅ 安全：捕获所有异常，返回错误信息让 LLM 自行处理
@tool
def safe_api_call(query: str) -> str:
    """调用外部 API 查询信息"""
    try:
        resp = requests.get(f"https://api.example.com/{query}", timeout=10)
        resp.raise_for_status()
        return resp.json()["result"]
    except requests.Timeout:
        return "API 调用超时（10s），请稍后重试"
    except requests.HTTPError as e:
        return f"API 返回错误: HTTP {e.response.status_code}"
    except Exception as e:
        return f"调用失败: {str(e)}"
```

#### 坑 4：生产环境用 `MemorySaver`，重启后状态丢失

```python
# ❌ 开发用的，进程重启后所有会话状态消失
checkpointer = MemorySaver()

# ✅ 生产用 PostgreSQL，持久化到数据库
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg

conn = psycopg.connect("postgresql://user:pass@host:5432/db")
checkpointer = PostgresSaver(conn)
checkpointer.setup()  # 首次运行初始化数据库表

graph = builder.compile(checkpointer=checkpointer)
```

### 5.2 性能优化实践

```python
# ① 异步节点：提升并发吞吐
async def async_agent_node(state: AgentState) -> dict:
    response = await llm.ainvoke(state["messages"])  # 异步调用
    return {"messages": [response]}

# ② Fan-out 并行执行：多个独立任务同时跑
builder.add_edge("start", "task_a")
builder.add_edge("start", "task_b")  # task_a 和 task_b 并行执行
builder.add_edge("task_a", "merge")
builder.add_edge("task_b", "merge")  # 都完成后汇聚到 merge 节点

# ③ 消息裁剪：防止 Context 超长导致费用暴增
from langchain_core.messages import trim_messages

def agent_node_with_trim(state: AgentState) -> dict:
    # 只保留最近 20 条消息，避免 Token 超限
    trimmed = trim_messages(
        state["messages"],
        max_tokens=4000,
        strategy="last",
        token_counter=llm
    )
    response = llm_with_tools.invoke(trimmed)
    return {"messages": [response]}
```

### 5.3 安全加固清单

| 风险 | 描述 | 防范措施 |
| --- | --- | --- |
| Prompt 注入 | 用户输入恶意指令劫持 Agent | 输入过滤 + 系统提示词加固 |
| 工具权限滥用 | Agent 调用危险操作（删库等） | 工具白名单 + Human-in-Loop 审核 |
| 敏感数据泄露 | 用户数据进入第三方 LLM | 数据脱敏 + 私有化部署 |
| 费用失控 | 无限循环导致 Token 爆炸 | 最大迭代次数 + Token 预算限制 |
| 幻觉传播 | 错误信息在多步中被放大 | 关键步骤添加验证节点 |

### 5.4 生产最佳实践 Checklist

**✅ State 设计**

- ☐ TypedDict 明确定义所有字段
- ☐ 消息列表必须用 `add_messages` 归约函数
- ☐ 加入 `iteration_count` 字段防无限循环

**✅ 节点设计**

- ☐ 每个节点职责单一（单一职责原则）
- ☐ 工具函数必须捕获异常，返回错误描述
- ☐ 耗时操作使用 `async / await` 异步节点

**✅ 持久化配置**

- ☐ 开发环境：`MemorySaver`（零配置）
- ☐ 测试环境：`SqliteSaver`（本地文件）
- ☐ 生产环境：`PostgresSaver`（高可用）
- ☐ `thread_id` 规范：`user_{uid}_session_{sid}`

**✅ 可观测性**

- ☐ 接入 LangSmith（3 行环境变量）
- ☐ 关键节点打印日志（node name + state summary）
- ☐ 设置 Token 消耗和延迟告警

**✅ 测试策略**

- ☐ 单元测试：每个节点函数独立测试
- ☐ 集成测试：完整图流程 E2E 测试
- ☐ 回归测试：LangSmith Dataset + `evaluate()`

### 5.5 学习路线图

> *[图片：LangGraph 学习路线图]*

**推荐学习资源**：

| 资源 | 地址 | 说明 |
| --- | --- | --- |
| 官方文档 | <https://langchain-ai.github.io/langgraph/> | 最权威参考，必读 |
| LangGraph Academy | <https://academy.langchain.com/> | 官方免费课程 |
| GitHub 示例 | <https://github.com/langchain-ai/langgraph> | 官方 Cookbook |
| LangSmith 文档 | <https://docs.smith.langchain.com/> | 运维平台文档 |
| 本文脚手架 | `langgraph-fastapi-multi-agent` | 开箱即用工程模板 |

---

## 六、🚀 脚手架工程：快速搭建你的第一个 Agent 项目

为了帮助大家快速上手，我整理了一套开箱即用的 LangGraph 脚手架工程，包含：

- ✅ 完整的项目结构和依赖配置
- ✅ ReAct Agent / Plan&Execute / 多 Agent 三种模式示例
- ✅ SQLite + PostgreSQL 持久化配置
- ✅ LangSmith 可观测性接入
- ✅ 异步流式输出示例
- ✅ 单元测试 + 集成测试模板

📦 **脚手架工程地址**：

🔗 `langgraph-fastapi-multi-agent`（脚手架工程）　← 链接待补充

> *[图片：脚手架项目结构图]*

**推荐项目结构**：

```text
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
│   │
│   ├── tools/
│   │   ├── search_tools.py       # 搜索类工具
│   │   ├── code_tools.py         # 代码执行工具
│   │   └── data_tools.py         # 数据查询工具
│   │
│   ├── state/
│   │   └── schemas.py            # 所有 State TypedDict 定义
│   │
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

**5 分钟快速启动**：

```bash
# 1. 克隆脚手架
git clone <脚手架工程地址>
cd langgraph-scaffold

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY 和 LANGCHAIN_API_KEY

# 4. 运行示例 Agent
python scripts/run_agent.py --mode react --query "北京今天天气怎么样？"
```

> 📌 本仓库 `langgraph-scaffold/` 即按本章推荐结构 1:1 落地，并补全了原文中"链接待补充"的实际可运行代码（含 Mock LLM 模式，无 API Key 也可跑通）。

---

## 七、总结

> *[图片：总结 / 全文导图]*

**一句话总结**：如果你要在生产环境构建需要多步推理、工具调用、状态管理、人机协作的 AI Agent，**LangGraph 是目前 Python 生态中最成熟、最灵活的选择**。

**什么时候不用 LangGraph**：简单的单轮问答、RAG 检索、不需要循环的线性流程——直接用 LangChain LCEL 就够了，**不要过度设计**。

> 📌 **版本说明**：本文基于 LangGraph 0.2.x 编写，框架迭代较快，建议结合官方文档使用。
> 💬 **欢迎交流**：如果你在实践中遇到问题，或者有更好的实践经验，欢迎在评论区留言讨论！
> 👍 如果对你有帮助，欢迎点赞收藏，转发给有需要的同学～

---

## 附录：原文统计 & 元信息

| 项 | 值 |
| --- | --- |
| 原文 ID | 656075 |
| 标签 | `agent` · `AI` · `LangGraph` |
| 发布 | 2026-03-30 11:36:01（更新于 2026-04-08 14:21:42） |
| 阅读 / 点赞 / 收藏 / 评论 | 1629 / 28 / 111 / 4 |
| KM 推荐 / 头条 | 是 / 是 |
| 热度 | 53 |
| 附件 | `langgraph-fastapi-multi-agent-main.zip` |
| 链接 | <https://km.woa.com/articles/show/656075?jumpfrom=kmmcp> |

> 数据来源：KM MCP · 整理时间：2026-05-19

# langgraph-scaffold

> 基于 KM 文章 [《LangGraph实战指南：从入门到生产级 AI Agent 开发》](https://km.woa.com/articles/show/656075?jumpfrom=kmmcp) 第六章「脚手架工程」的可复现实现。
>
> 一套开箱即用的 LangGraph 脚手架，演示 ReAct / Plan&Execute / Multi-Agent 三种主流 Agent 模式，集成 SQLite/Postgres 持久化与 LangSmith 可观测性。

## ✨ 特性

- ✅ 完整目录结构（state / tools / agents / checkpointers / tests / scripts）
- ✅ 三种 Agent 模式：ReAct、Plan & Execute、Multi-Agent
- ✅ 三种持久化：MemorySaver / SqliteSaver / PostgresSaver 通过工厂统一切换
- ✅ LangSmith 可观测性接入（3 行环境变量，零代码侵入）
- ✅ 流式输出、异步节点、消息裁剪、迭代次数防护等生产实践
- ✅ 单元测试 + 集成测试模板（pytest）
- ✅ CLI 快速运行入口（`scripts/run_agent.py`）
- ✅ 离线 Mock LLM 模式：`MOCK_LLM=1` 时无需任何 API Key 即可跑通整个流程，方便学习与 CI

## 📁 项目结构

```
langgraph-scaffold/
├── README.md
├── requirements.txt
├── .env.example                  # 环境变量模板
│
├── app/
│   ├── __init__.py
│   ├── settings.py               # 统一配置（OpenAI Key / LangSmith / DB 等）
│   ├── llm.py                    # LLM 工厂（含 Mock 模式）
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── react_agent.py        # ReAct Agent 示例
│   │   ├── plan_execute_agent.py # Plan & Execute 示例
│   │   └── multi_agent.py        # 多 Agent 协作示例（Supervisor 模式）
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── search_tools.py       # 搜索类工具
│   │   ├── code_tools.py         # 代码执行工具（安全的表达式计算）
│   │   └── data_tools.py         # 数据查询工具
│   │
│   ├── state/
│   │   ├── __init__.py
│   │   └── schemas.py            # 所有 State TypedDict 定义
│   │
│   └── checkpointers/
│       ├── __init__.py
│       └── setup.py              # Checkpointer 工厂函数
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_nodes.py             # 节点单元测试
│   └── test_graphs.py            # 图集成测试
│
├── scripts/
│   └── run_agent.py              # 快速运行入口
│
└── docs/
    └── ARTICLE_DIGEST.md         # 原文章整理（含核心知识点）
```

## 🚀 5 分钟快速启动

```bash
# 1. 进入项目
cd langgraph-scaffold

# 2. 安装依赖（建议使用 venv / conda 隔离）
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env       # Windows: copy .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY（无 Key 时设置 MOCK_LLM=1）

# 4. 跑示例（三种模式任选）
python scripts/run_agent.py --mode react        --query "北京今天天气怎么样？顺便算一下 123 * 456"
python scripts/run_agent.py --mode plan-execute --query "查一下深圳天气并计算 88*99，最后告诉我结论"
python scripts/run_agent.py --mode multi        --query "帮我查一下杭州的天气，并算 1+2+3+4+5"

# 5. 跑测试
pytest -q
```

> 💡 第一次跑可以直接 `set MOCK_LLM=1`（PowerShell：`$env:MOCK_LLM=1`），脚手架内置一个最小 Mock LLM，会自动调用工具并返回固定结果，整个流程可在**完全离线**情况下跑通。

## 🔑 环境变量说明（`.env`）

| 变量 | 作用 | 示例 |
| --- | --- | --- |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-...` |
| `OPENAI_MODEL` | 模型名 | `gpt-4o-mini` |
| `MOCK_LLM` | 设为 `1` 启用离线 Mock LLM（无需 Key） | `1` |
| `CHECKPOINTER` | 选择持久化：`memory` / `sqlite` / `postgres` | `sqlite` |
| `SQLITE_PATH` | SQLite 文件路径 | `./.checkpoints.sqlite` |
| `POSTGRES_DSN` | Postgres 连接串 | `postgresql://user:pass@host:5432/db` |
| `LANGCHAIN_TRACING_V2` | 开启 LangSmith 追踪 | `true` |
| `LANGCHAIN_API_KEY` | LangSmith Key | `lsv2_...` |
| `LANGCHAIN_PROJECT` | LangSmith 项目名 | `langgraph-scaffold` |

## 🧱 三种 Agent 模式速览

| 模式 | 适用场景 | 入口 |
| --- | --- | --- |
| **ReAct** | 单步推理→工具调用→观察循环，最常用 | `app/agents/react_agent.py` |
| **Plan & Execute** | 复杂任务、需要先规划再执行 | `app/agents/plan_execute_agent.py` |
| **Multi-Agent** | 多角色分工协作（Supervisor 路由） | `app/agents/multi_agent.py` |

## 🛡️ 生产最佳实践（已内置）

- 🔒 `iteration_count` 字段 + 上限 = 防 Agent 无限循环
- 🔁 `add_messages` 归约函数 = 防消息历史被覆盖
- 🧱 工具函数全部 `try/except` = 防单个工具崩溃整张图
- 💾 PostgresSaver 工厂 = 生产环境状态持久化
- 📊 LangSmith 接入 = 全链路追踪开箱即用

## 📖 配套阅读

- 原文完整整理（结构化 Markdown，含全部代码与表格）：[`docs/LangGraph实战指南-原文整理.md`](docs/LangGraph实战指南-原文整理.md)
- 文章精炼摘要 + 与本仓库的对照：[`docs/ARTICLE_DIGEST.md`](docs/ARTICLE_DIGEST.md)
- LangGraph 官方文档：<https://langchain-ai.github.io/langgraph/>
- LangSmith 文档：<https://docs.smith.langchain.com/>

## 📌 版本说明

基于 LangGraph 0.2.x；框架迭代较快，跑通后建议结合官方文档同步最新 API。

## License

仅用于学习交流，对应 KM 原文与官方框架的版权归原作者所有。

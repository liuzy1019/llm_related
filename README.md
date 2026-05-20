# llm_related

> LLM / AI Agent 学习与实践相关的项目合集。

本仓库收录个人在大语言模型、AI Agent、提示工程、检索增强等方向的可运行示例、脚手架与学习笔记，每个子目录是一个独立可跑的项目。

## 📦 项目索引

| 项目 | 说明 | 入口 |
| --- | --- | --- |
| **langgraph-scaffold** | LangGraph 生产级 Agent 脚手架：ReAct / Plan & Execute / Multi-Agent 三种模式 + 持久化 + LangSmith + 测试模板，内置 Mock LLM 离线可跑 | [`langgraph-scaffold/`](langgraph-scaffold/) |

> 后续会继续往这里加新的 LLM 相关项目子目录（RAG、Prompt 工程、Eval、Fine-tune 等）。

## 🔖 项目背景

每个子目录通常都包含：

- `README.md`：项目说明与启动命令
- `requirements.txt`：依赖清单
- `docs/`：相关原始文章 / 学习整理
- `tests/`：可运行的测试用例

## 📌 通用说明

- 大部分项目使用 Python 3.10+ ，建议每个子项目独立创建虚拟环境
- 涉及 OpenAI / Claude / 本地模型时，请按各自 `.env.example` 配置 API Key
- 推荐结合 [LangSmith](https://docs.smith.langchain.com/) 做可观测性调试

## License

详见 [LICENSE](LICENSE)。

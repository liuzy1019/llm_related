# llm_related

> LLM / AI Agent 学习与实践相关的项目合集。

本仓库收录个人在大语言模型、AI Agent、提示工程、检索增强、RL/RLHF 与从零预训练等方向的可运行示例、脚手架与学习笔记，每个子目录是一个独立可跑的项目。

> 📅 **最近更新：2026-05-25** ｜ 维护约定：**每次 `git commit` 之前都要更新本 README** —— 至少同步「项目索引表」和顶部的「最近更新」日期，让仓库首页始终反映最新结构。

---

## 📦 项目索引

| 项目 | 类型 | 说明 | 入口 |
| --- | --- | --- | --- |
| **langgraph-scaffold** | 脚手架 | LangGraph 生产级 Agent 脚手架：ReAct / Plan & Execute / Multi-Agent 三种模式 + SQLite/Postgres 持久化 + LangSmith 可观测性 + 测试模板，内置 Mock LLM 离线可跑 | [`langgraph-scaffold/`](langgraph-scaffold/) |
| **hxim-main** | 应用 | 基于浣熊食堂客服方案的 Hybrid Coordinator 客服 Agent：Router / Knowledge / Action / Hybrid / Generator / Memory，离线规则模式可跑，含 FastAPI 入口 | [`hxim-main/`](hxim-main/) |
| **rl-main** | 笔记库 | 大模型 RL / RLHF / GRPO / reasoning / 推理基础设施 notebook 笔记库，覆盖 RL 基础、verl、vLLM、SGLang、Ray、Agent RL、K2 等主题 | [`rl-main/`](rl-main/) |
| **llm_pretrain** | 复现项目 | 从零复现 7B 类 LLaMA：Tokenizer (BPE 64k) → Megatron-LM 预训练 → HF 转换 → Verl SFT → 评测，配套 KM #660614 原文整理 | [`llm_pretrain/`](llm_pretrain/) |

> 后续会继续往这里加新的 LLM 相关项目子目录（RAG、Prompt 工程、Eval、Fine-tune、MCP 等）。

---

## 🗂️ 仓库结构

```
llm_related/
├── README.md                 # ← 你正在看的文件，每次提交前更新
├── LICENSE
├── .gitignore
│
├── langgraph-scaffold/       # LangGraph 脚手架（25 个文件）
├── hxim-main/                # 浣熊客服 Agent（22 个文件）
├── rl-main/                  # RL/RLHF notebook 笔记（169 个文件）
└── llm_pretrain/             # 7B LLM 从零预训练复现（README + docs，子目录占位中）
```

每个子目录通常都包含：

- `README.md`：项目说明与启动命令
- `requirements.txt`：依赖清单（仅 `llm_pretrain` 暂未提供）
- `docs/`：相关原始文章 / 学习整理
- `tests/`：可运行的测试用例（适用于应用类项目）

---

## 📌 通用说明

- 大部分项目使用 **Python 3.10+**，建议每个子项目独立创建虚拟环境（`venv` / `conda`）
- 涉及 OpenAI / Claude / 本地模型时，请按各自子目录下的 `.env.example` 配置 API Key
- LangGraph 类项目推荐结合 [LangSmith](https://docs.smith.langchain.com/) 做可观测性调试
- `rl-main` / `llm_pretrain` 中的训练 / 推理示例通常需要 GPU + CUDA 环境
- 模型权重、训练 checkpoint、wandb / tensorboard 日志、原始数据等大文件**默认不入库**（见各子项目 `.gitignore`）

---

## 🔁 维护约定

为了让仓库首页一直保持"看 README 就能知道里面有啥"的状态，约定：

1. **每次 `git commit` 前**：检查并更新本 README 的两个位置 —— 顶部 `最近更新` 日期、`项目索引` 表格。
2. **新增子项目**：在 `项目索引` 和 `仓库结构` 两个区块各加一行。
3. **重大变更**（拆分/重命名/废弃子项目）：先改 README 再改目录，确保 README 对应一次有意义的 commit。
4. **小型 bugfix / 文档微调**：可只更新 `最近更新` 日期，无需改表格。

---

## License

详见 [LICENSE](LICENSE)。各子项目内若有独立 License 声明，以其自身为准。

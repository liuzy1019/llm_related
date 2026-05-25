# Roadmap

> v1.0 之后的每日发版计划，用来把当前 demo 级核心链路逐步补齐为食堂外卖 IM 客服系统原型。

## 当前结论

当前 `v1.2` 约覆盖完整方案的 **52%**。它已经能演示 Router 分流、订单/配送/售后 mock 数据、8 个业务函数、食品安全转人工、缺槽位追问、多轮会话和二次确认闭环；但还没有 Agent Loop、ChromaDB 记忆/RAG、LLM Prompt、Benchmark 和可观测性。

## 模块差距

| 状态 | 模块 | 当前说明 |
| --- | --- | --- |
| 已完成 | `POST /chat` | FastAPI 接口可用，支持单轮请求 |
| 已完成 | 五路由决策 | 支持 `KNOWLEDGE / ACTION / HYBRID / CHITCHAT / ESCALATE` |
| 已完成 | 8 个业务函数 | 具备 demo 版订单、配送、退款、取消、投诉等函数 |
| 已完成 | 模拟数据库 | 具备用户、订单、配送、退款资格、食品安全险数据 |
| 部分完成 | Step 0 记忆召回 | 仅有 mock 用户画像，没有三层记忆和 ChromaDB |
| 部分完成 | Step 0.5 文本纠正 | 仅有少量领域 typo map，没有 LLM 兜底 |
| 部分完成 | Step 1 意图识别 | 关键词规则版，没有向量 Tier-1 和 LLM Tier-2 |
| 部分完成 | Step 2 阶段判断 | 简单 intent 映射，没有五信号融合 |
| 部分完成 | Step 3 情感检测 | 简单词典版，没有反讽/隐含情绪识别 |
| 部分完成 | Step 6 槽位提取 | 仅提订单号、手机号和少量 hint |
| 部分完成 | Step 8 RAG | 内存知识片段，没有 ChromaDB/Embedding/相似度过滤 |
| 部分完成 | Step 9 回复生成 | 模板拼接，没有 SOP + RAG + 函数结果注入 LLM |
| 已完成 | `POST /reset/{session_id}` | v1.1 已支持按 session_id 重置进程内会话状态 |
| 已完成 | 多轮会话 | v1.1 已支持缺槽位续接：保存 pending intent、pending slots 和 missing slots |
| 已完成 | 二次确认闭环 | v1.2 已保存 pending mutation，支持用户“确认/取消”后提交或终止 mock 操作 |
| 未完成 | Step 1.5 话题切换与书签 | 还不能临时插问后恢复任务 |
| 未完成 | Step 7 历史压缩 | 没有多轮历史压缩 |
| 未完成 | Agent Loop | 没有 Think -> Act -> Observe -> Decide 循环 |
| 未完成 | JSON 声明式配置 | 缺 `intents.json / functions.json / sop.json` |
| 未完成 | LLM/Prompt | 未接入 DeepSeek、结构化输出和 12 个 Prompt 模板 |
| 未完成 | Benchmark/可观测性 | 缺自动评测、LangSmith/OpenTelemetry |

## 每日版本路线

| 版本 | 目标 | 用户故事 | 主要改动 | 验收命令 | 演示 Query | Tag |
| --- | --- | --- | --- | --- | --- | --- |
| `v1.1` | 多轮会话、`POST /reset/{session_id}`、会话状态保存 | 用户先说“我要退款”，再补“778899”，系统能继承退款意图继续处理 | 已完成：session store、pending slots、reset API；CLI/API 均支持同一 session 连续对话 | `.venv/bin/python -m pytest -q tests` | `我要退款` -> `778899` | 是 |
| `v1.2` | 二次确认闭环 | 用户说“取消订单888888”，系统询问确认；用户说“确认”后生成 mock 操作结果 | 已完成：保存 pending mutation；支持“确认/取消”；mock DB 记录操作事件 | `.venv/bin/python -m pytest -q tests` | `取消订单888888` -> `确认` | 是 |
| `v1.3` | 声明式配置 | 新增意图/函数/SOP 时优先改 JSON，不改主流程代码 | 新增 `intents.json / functions.json / sop.json`；Router 和业务函数从配置读取关键元数据 | `.venv/bin/python -m pytest -q tests` | `订单778899漏发了，我要退款` | 是 |
| `v1.4` | 工单系统 | 退款、投诉、食品安全场景能生成可查询 ticket | mock DB 增加 ticket 表；售后/投诉/转人工生成 ticket_id；API 暴露 demo ticket 查询 | `.venv/bin/python -m pytest -q tests` | `订单123456吃出塑料了，我肚子疼` | 是 |
| `v1.5` | Web Chat Demo | 演示时可以在网页聊天，并看到路由/槽位/trace | 新增轻量 Web 页面；展示 reply、intent、route、slots、trace、function_results | `.venv/bin/python -m pytest -q tests` | 页面输入配送、退款、食品安全场景 | 是 |
| `v1.6` | Agent Loop demo | “查配送并催单”可展示多步函数链路 | 实现 Think -> Act -> Observe -> Decide 的确定性 demo loop；限制最多 3 轮 | `.venv/bin/python -m pytest -q tests` | `我的订单123456到哪了，帮我催一下` | 是 |
| `v1.7` | 话题切换与书签恢复 | 用户退款中途问营业时间，回答后可回到退款流程 | 增加 bookmark state；识别 temporary/permanent topic switch；恢复 pending task | `.venv/bin/python -m pytest -q tests` | `我要退款` -> `你们几点营业` -> `继续退款` | 是 |
| `v1.8` | ChromaDB/向量 RAG demo | 知识类问题从向量库检索，并返回来源片段 | 接入 ChromaDB demo collections；products/faq/policies 分集合检索；保留内存 fallback | `.venv/bin/python -m pytest -q tests` | `退款多久到账`、`有什么不辣的菜` | 是 |
| `v1.9` | LLM Router/Generator | 可在 mock 和真实模型之间切换 | 接入 DeepSeek/OpenAI-compatible LLM；Router structured output；Generator 使用 SOP/RAG/函数结果生成 | `.venv/bin/python -m pytest -q tests` | 长句、多意图、模糊售后问题 | 是 |
| `v2.0` | Benchmark、可观测性、完整演示脚本 | 每次发版可以量化延迟、准确率、完成率 | 增加 50 条 demo benchmark；输出报告；接入 LangSmith/OpenTelemetry trace | `.venv/bin/python -m pytest -q tests` + benchmark 命令 | 全量场景集 | 是 |

## 每日发版规则

1. 每个版本只做一个主要目标，保证当天可演示。
2. 每次发版前必须通过测试：
   ```bash
   cd hxim-main
   .venv/bin/python -m pytest -q tests
   ```
3. 每次发版必须更新 `README.md` 或本文件，记录新增能力和演示 Query。
4. 每次发版必须更新 `docs/PROGRESS_LOG.md`，记录当天完成内容、验证结果和下一步。
5. 每次发版必须遵守 `docs/RELEASE_PROCESS.md`。
6. 每次发版必须打 tag，例如：
   ```bash
   git tag -a v1.1 -m "hx customer service agent v1.1"
   ```
7. 不提交本地凭据、token、`.venv/`、`.pytest_cache/` 或其它无关项目改动。

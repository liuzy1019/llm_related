# hxim-main

> 基于 `hx_im` 两份浣熊食堂客服方案实现的 LangGraph agent 项目骨架。

该项目参考 `langgraph-scaffold` 的目录和编码习惯，将方案中的 13 步 Pipeline 渐进演进为 `Hybrid Coordinator`：

- `Router Agent`：合并原 Step 0-5，负责文本纠正、意图、阶段、情感、转人工和路由。
- `Knowledge Agent`：承接 Step 6 + Step 8，按意图检索知识。
- `Action Agent`：承接 Step 6 + Step 8.5，封装 8 个业务函数和二次确认。
- `Hybrid Agent`：并行思想的落地点，同时整合知识和业务函数结果。
- `Generator Agent`：承接 Step 9，生成最终回复。
- `Memory Agent`：承接 Step 10，提取长期事实。

当前版本默认离线可跑，所有 LLM/RAG/业务接口位置都先用确定性规则和 mock 数据占位，方便后续逐步替换。

## 项目结构

```text
hxim-main/
├── app/
│   ├── agents/customer_service_graph.py
│   ├── domain/catalog.py
│   ├── domain/heuristics.py
│   ├── state/schemas.py
│   ├── tools/business_tools.py
│   ├── api.py
│   └── settings.py
├── docs/ARCHITECTURE.md
├── docs/ROADMAP.md
├── docs/PROGRESS_LOG.md
├── docs/RELEASE_PROCESS.md
├── scripts/run_chat.py
├── tests/
├── requirements.txt
└── .env.example
```

## 项目文档

- [Architecture](docs/ARCHITECTURE.md)：当前 LangGraph 编排与浣熊客服方案的映射。
- [Roadmap](docs/ROADMAP.md)：v1.0 之后的每日发版计划与完整方案差距。
- [Progress Log](docs/PROGRESS_LOG.md)：每日系统进度、验证结果和下一步记录。
- [Release Process](docs/RELEASE_PROCESS.md)：每日版本发布、tag、推送和回滚规范。

## 快速启动

```bash
cd hxim-main
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/run_chat.py --query "我的订单123456到哪了，帮我催一下"
python scripts/run_chat.py --query "订单123456吃出所料了，我要投诉"
python scripts/run_chat.py --query "取消订单888888"
```

启动 API：

```bash
uvicorn app.api:app --reload --port 8000
```

请求示例：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"query":"我的订单123456到哪了，帮我催一下"}'
```

Demo 订单：

| 订单号 | 场景 | 可试 Query |
| --- | --- | --- |
| `123456` | 配送中、支持食品安全险 | `我的订单123456到哪了，帮我催一下` |
| `888888` | 商家制作中、可取消 | `取消订单888888` |
| `778899` | 已送达、适合售后/退款 | `订单778899漏发了，我要退款` |

API 启动后可访问 `GET /demo/orders` 查看模拟订单数据。

## 测试

```bash
pytest -q
```

## 后续替换点

- 将 `app/domain/catalog.py` 替换为 ChromaDB 的 `products / faq / policies` 三集合检索。
- 将 `app/domain/heuristics.py` 的 Router 规则替换为结构化 LLM 输出。
- 将 `app/tools/business_tools.py` 的 mock 函数替换为真实订单、配送、售后接口。
- 为 `build_customer_service_graph()` 增加 checkpointer 和 LangSmith/OpenTelemetry 追踪。

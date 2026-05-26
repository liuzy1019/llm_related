# Architecture

## 来源映射

本项目抽象自食堂外卖 IM 客服场景的两类设计输入：

- 多步骤客服 Pipeline：覆盖记忆召回、文本纠错、意图识别、阶段判断、情感识别、转人工、槽位提取、RAG、函数执行、回复生成和事实提取。
- Hybrid Coordinator 架构：将规则路由、知识检索、业务动作和回复生成拆成可替换的 LangGraph 节点。

## Pipeline 到 Agent 的映射

| 原步骤 | 当前项目节点 | 说明 |
| --- | --- | --- |
| Step 0 记忆召回 | `router_agent` / `memory_agent` | 目前使用轻量内存快照占位 |
| Step 0.5 文本纠正 | `router_agent` | 规则实现，如“吃出所料”纠正为“吃出塑料” |
| Step 1 意图识别 | `router_agent` | 从 `app/configs/intents.json` 读取关键词和置信度，可替换为 LLM structured output |
| Step 2 阶段判断 | `router_agent` | 从 `app/configs/intents.json` 读取 `presale / sale / after_sale / general` |
| Step 3 情感检测 | `router_agent` | 正负向词典 |
| Step 4 转人工判断 | `router_agent` | 人工请求、食品安全、敏感词优先升级 |
| Step 5 路由决策 | `route_from_router` | 从 `app/configs/intents.json` 读取路由元数据，再分发到下游节点 |
| Step 6 槽位提取 | `router_agent` | 订单号、手机号、食品安全槽位 |
| Step 8 RAG | `knowledge_agent` | 离线知识库占位 |
| Step 8.5 函数执行 | `action_agent` | 从 `app/configs/functions.json` 读取意图到函数序列，变更类强制确认 |
| Step 9 回复生成 | `generator_agent` | 汇总知识和函数结果，基础 SOP 文案来自 `app/configs/sop.json` |
| Step 10 事实提取 | `memory_agent` | 提取口味偏好、过敏信息 |

## Graph

```text
START
  |
router
  |-- ESCALATE / CHITCHAT --> generator
  |-- KNOWLEDGE -----------> knowledge --> generator
  |-- ACTION --------------> action ----> generator
  |-- HYBRID --------------> hybrid ----> generator
                                              |
                                           memory
                                              |
                                             END
```

## Demo Database

演示版新增 `app/data/mock_database.py`，模拟真实业务系统中的几类数据：

- 用户画像：手机号脱敏、默认地址、口味偏好、过敏信息。
- 订单：商家、菜品、金额、订单状态、是否可取消、是否可退款。
- 配送：骑手、距离、预计送达时间、最近事件。
- 食品安全险：用于食品安全 P0 场景演示。

当前业务函数不再返回固定文本，而是通过 `MOCK_DB` 查询订单状态。API 额外提供 `GET /demo/orders`，方便演示前查看可用订单。

## Declarative Config

v1.3 起，核心规则元数据从 Python 硬编码迁移到 JSON 配置：

- `app/configs/intents.json`：标准意图、关键词、置信度、阶段、路由和缺订单号时的路由回退。
- `app/configs/functions.json`：意图到业务函数的执行序列，以及 `requested_action=cancel_order` 等槽位覆盖规则。
- `app/configs/sop.json`：生成器使用的缺槽位提示、确认提示、兜底回复和转人工回复。

`app/domain/config_loader.py` 负责加载和校验这些配置，确保标准意图覆盖完整、动作序列只引用已注册函数、SOP 分区存在。

## 实现原则

- 节点只返回局部 state 更新。
- 追加型字段使用 reducer，避免覆盖历史 trace、RAG 和函数结果。
- 业务变更函数只生成 `needs_confirmation`，不直接执行破坏性操作。
- 离线规则只是第一阶段脚手架，目标是让工程结构先稳定，再逐个替换节点。

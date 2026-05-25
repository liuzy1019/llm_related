# Progress Log

> 每日系统进度记录。每次发版或完成关键里程碑后，在这里追加一条，记录当天完成内容、验证结果、剩余风险和下一步。

## 记录格式

| 日期 | 版本/阶段 | 完成内容 | 验证结果 | 当前覆盖度 | 下一步 |
| --- | --- | --- | --- | --- | --- |

## 日志

| 日期 | 版本/阶段 | 完成内容 | 验证结果 | 当前覆盖度 | 下一步 |
| --- | --- | --- | --- | --- | --- |
| 2026-05-21 | `v1.0` | 建立 `hxim-main` 项目骨架；实现 Router/Knowledge/Action/Hybrid/Generator/Memory 图；加入 mock 订单数据库、8 个业务函数、`POST /chat`、`GET /demo/orders`、CLI demo 和测试。 | `.venv/bin/python -m pytest -q tests` 通过，9 passed。 | 约 40%，可演示单轮客服核心链路。 | `v1.1`：多轮会话、`POST /reset/{session_id}`、会话状态保存。 |
| 2026-05-21 | 文档整理 | 新增 `docs/ROADMAP.md`，明确从 `v1.1` 到 `v2.0` 的每日发版计划；新增本进度日志模板并在 README/ROADMAP 中建立入口。 | 文档更新后继续运行测试，9 passed。 | 覆盖度不变，项目管理信息更完整。 | 每日开发后同步更新本日志，并在发版时记录 tag。 |
| 2026-05-21 | 工程规范 | 新增 `docs/RELEASE_PROCESS.md`，明确每日发版、测试、tag、推送、回滚和安全规则；补充 `.gitignore` 的 token/secret/`*_git.md` 忽略规则。 | `.venv/bin/python -m pytest -q tests` 通过，9 passed。 | 覆盖度不变，工程流程风险降低。 | 后续补 CI、CHANGELOG、PR/Issue 模板。 |
| 2026-05-22 | `v1.1` 开发 | 新增 session-aware `ChatService`、进程内 `SessionStore`、`POST /reset/{session_id}`、CLI `--interactive`；支持“我要退款”->“778899”和“帮我催单”->“123456”的缺槽位续接；新增真实会话流测试，并修复食品安全/投诉等高优先级新意图被 pending intent 误吞的问题。 | `.venv/bin/python -m pytest -q tests` 通过，17 passed；覆盖多轮、session 隔离、reset、食品安全中断、完成后继续问答。 | 约 48%，已具备 demo 级多轮会话能力。 | `v1.2`：二次确认闭环，用户说“确认/取消”后继续执行或取消 pending mutation。 |
| 2026-05-25 | `v1.2` 开发 | 按变更类动作二次确认流程实现 pending mutation；取消订单、退款申请等变更类函数先进入待确认状态，用户说“确认”后提交 mock 操作，说“取消”后终止；mock DB 记录取消/退款事件，并补充测试隔离 reset。 | `.venv/bin/python -m pytest -q tests` 通过，19 passed；`.venv/bin/python -m compileall -q app scripts tests database` 通过。 | 约 52%，已具备 demo 级多轮 + 二次确认闭环。 | `v1.3`：声明式配置，将意图、函数、SOP 元数据抽到 JSON。 |

## 维护规则

1. 每天只追加，不改历史记录；如果历史有误，在新记录里说明修正。
2. 每条记录必须包含验证结果，至少写明是否运行测试。
3. 如果当天创建 tag，在“版本/阶段”中写明 tag，例如 `v1.1`。
4. 不在日志中记录 token、账号密码、私有凭据或本地敏感路径。

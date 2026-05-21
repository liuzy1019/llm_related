# Release Process

> `hxim-main` 的每日发版规范。目标是让每个版本都可验证、可回滚、可追踪，并避免把本地凭据或无关改动带进发布。

## 版本规则

- 版本号采用 `vMAJOR.MINOR`，例如 `v1.1`、`v1.2`、`v2.0`。
- 每天最多发布一个主版本；同一天修复发布可使用 `v1.1.1`。
- 每个版本只聚焦一个主要目标，避免把工程化、业务功能和重构混在一个发布里。
- `main` 始终保持可运行；未完成工作使用本地分支或 feature 分支隔离。

## 发布前检查

发布前必须确认：

```bash
git status --short
```

要求：

- 只包含本次发布相关文件。
- 不包含 token、账号密码、`.env`、`*_git.md`、`.venv/`、`.pytest_cache/`。
- 不混入 `langgraph-scaffold`、`hx_im` 或其它无关目录改动。

运行测试：

```bash
cd hxim-main
.venv/bin/python -m pytest -q tests
```

至少手动跑 2 条 demo query：

```bash
.venv/bin/python scripts/run_chat.py --query "我的订单123456到哪了，帮我催一下"
.venv/bin/python scripts/run_chat.py --query "订单123456吃出所料了，我肚子疼"
```

## 文档要求

每次发布必须同步更新：

- `docs/PROGRESS_LOG.md`：记录版本、完成内容、测试结果、覆盖度和下一步。
- `docs/ROADMAP.md`：如果路线、优先级或验收标准发生变化，需要更新。
- `README.md`：如果启动命令、API、demo query 或使用方式发生变化，需要更新。

## 提交流程

只暂存本次发布相关文件：

```bash
git add <files>
git diff --cached --stat
```

提交信息格式：

```bash
git commit -m "Release hx customer service agent v1.1"
```

如果只是工程化或文档优化，还没有形成正式版本：

```bash
git commit -m "Document hx customer service release process"
```

## Tag 与推送

正式版本发布时打 annotated tag：

```bash
git tag -a v1.1 -m "hx customer service agent v1.1"
```

推送分支和 tag：

```bash
git push origin main
git push origin v1.1
```

推送后确认：

```bash
git log --oneline --decorate -1
git status --short --branch
```

## 回滚策略

如果版本已经推送但发现问题：

1. 优先创建修复提交并发布 patch tag，例如 `v1.1.1`。
2. 如果必须回滚，使用 `git revert <commit>` 创建显式回滚提交，不使用 `git reset --hard` 改写远端历史。
3. 在 `docs/PROGRESS_LOG.md` 记录回滚原因、影响范围和修复计划。

## 安全规则

- GitHub token、API Key、账号密码只允许放在系统凭据管理器或仓库外部。
- 不把凭据写入 remote URL、README、日志、测试 fixture 或代码注释。
- 如果 token 曾经出现在聊天、终端输出或仓库目录内，视为已泄露，应立即 revoke 并重新生成。
- 发布前运行：
  ```bash
  git status --short
  ```
  确认没有 `*_git.md`、`.env`、`token`、`secret` 类文件进入暂存区。


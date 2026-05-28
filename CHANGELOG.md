# Changelog

All notable changes to this repository are documented in this file.

The format follows the spirit of [Keep a Changelog](https://keepachangelog.com/), and version entries are grouped by repository milestone. Project-specific implementation details for `hxim-main` are also tracked in [`hxim-main/docs/PROGRESS_LOG.md`](hxim-main/docs/PROGRESS_LOG.md).

## [Unreleased]

### Planned

- `hxim-main v1.4`: add a mock ticket system for refund, complaint, and food-safety escalation flows.
- Add benchmark and observability entries when the project reaches the `v2.0` milestone.

## [v1.3] - 2026-05-26

### Added

- Added declarative runtime configuration for `hxim-main`:
  - `hxim-main/app/configs/intents.json`
  - `hxim-main/app/configs/functions.json`
  - `hxim-main/app/configs/sop.json`
- Added `hxim-main/app/domain/config_loader.py` to load and validate runtime JSON config.
- Added config regression tests in `hxim-main/tests/test_config_loader.py`.

### Changed

- Refactored `hxim-main` Router metadata to read intent keywords, confidence, stage, and route from JSON config.
- Refactored business action sequencing to read intent-to-function plans from JSON config.
- Moved generator base SOP text into JSON config.
- Updated `hxim-main` architecture, roadmap, progress log, and README for the v1.3 config layer.

### Verified

- `hxim-main/.venv/bin/python -m pytest -q hxim-main/tests`
  - `28 passed`
- `hxim-main/.venv/bin/python -m compileall -q hxim-main/app hxim-main/scripts hxim-main/tests`

## [v1.2] - 2026-05-25

### Added

- Added session-aware `ChatService` and process-local `SessionStore`.
- Added multi-turn continuation for missing order ids.
- Added pending mutation support for mutating actions.
- Added confirmation and cancellation handling for refund and order-cancellation flows.
- Added IM auto-evaluation, dashboard, and annotation payload adapters.
- Added Supabase schema, Hive DDL, and Supabase-to-Hive sync scripts for evaluation data.
- Added realistic conversation and self-built data tests.

### Changed

- Expanded `hxim-main` mock database to support refund tickets, cancellation state, and order events.
- Extended CLI and FastAPI response surfaces with session and evaluation payloads.

### Verified

- `hxim-main/.venv/bin/python -m pytest -q hxim-main/tests`
  - `23 passed` after self-built data tests were added.

## [v1.1] - 2026-05-22

### Added

- Added multi-turn session state for pending intent, pending slots, missing slots, and conversation history.
- Added `POST /reset/{session_id}`.
- Added interactive CLI mode with `--interactive`.
- Added tests for session isolation, reset behavior, food-safety interruption, and completed-turn continuation.

### Fixed

- Prevented high-priority food-safety and human-escalation intents from being swallowed by a previous pending task.

### Verified

- `hxim-main/.venv/bin/python -m pytest -q hxim-main/tests`
  - `17 passed`

## [v1.0] - 2026-05-21

### Added

- Added the initial `hxim-main` LangGraph customer-service agent prototype.
- Implemented Router, Knowledge, Action, Hybrid, Generator, and Memory nodes.
- Added mock order, delivery, user, refund, and insurance data.
- Added FastAPI `POST /chat` and `GET /demo/orders`.
- Added CLI demo runner.
- Added initial domain, graph, and business function tests.
- Added release process, roadmap, and progress log documents.

### Verified

- `hxim-main/.venv/bin/python -m pytest -q hxim-main/tests`
  - `9 passed`

## Earlier Repository Milestones

### Added

- Added `rl-main`, a notebook collection for LLM RL, RLHF, GRPO, reasoning, and inference infrastructure topics.
- Added `llm_pretrain`, a from-scratch 7B-style LLM pretraining reproduction skeleton and notes.
- Added `langgraph-scaffold`, a runnable LangGraph scaffold for ReAct, Plan-and-Execute, and Multi-Agent patterns.

[Unreleased]: https://github.com/liuzy1019/llm_related/compare/v1.3...HEAD
[v1.3]: https://github.com/liuzy1019/llm_related/releases/tag/v1.3
[v1.2]: #v12---2026-05-25
[v1.1]: #v11---2026-05-22
[v1.0]: https://github.com/liuzy1019/llm_related/releases/tag/v1.0

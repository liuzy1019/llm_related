# hxim-main

Offline customer-service agent prototype for a food-delivery canteen scenario.

The project uses LangGraph to model a hybrid coordinator workflow. It runs without external LLM, RAG, order, or ticketing services by using deterministic routing rules, an in-memory mock database, and process-local session state.

## Features

- LangGraph workflow with Router, Knowledge, Action, Hybrid, Generator, and Memory nodes.
- Declarative JSON config for intent metadata, action sequences, and generator SOP text.
- Rule-based intent detection, slot extraction, stage classification, emotion detection, and escalation decision.
- Mock order, delivery, refund, cancellation, and user-profile data.
- Multi-turn session state for missing slots and pending mutations.
- Confirmation flow for mutating actions such as order cancellation and refund submission.
- FastAPI endpoints for chat, session reset, and demo order inspection.
- Evaluation payload adapters for auto-eval, dashboard, and annotation records.
- Supabase schema, Hive DDL, and Supabase-to-Hive sync script for evaluation data.
- Pytest coverage for graph execution, service orchestration, realistic conversation flows, and self-built test data.

## Architecture

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

Main modules:

| Module | Responsibility |
| --- | --- |
| `app/agents/customer_service_graph.py` | LangGraph nodes and graph wiring |
| `app/configs/` | Declarative intent, function, and SOP metadata |
| `app/domain/config_loader.py` | JSON config loading and validation |
| `app/domain/heuristics.py` | Rule-based normalization, intent detection, slot extraction, and routing helpers |
| `app/domain/catalog.py` | In-memory knowledge snippets used by the Knowledge node |
| `app/tools/business_tools.py` | Mock business actions for orders, delivery, refunds, cancellation, and modification |
| `app/data/mock_database.py` | In-memory users, orders, delivery records, and ticket state |
| `app/session_store.py` | Process-local conversation state |
| `app/service.py` | Session-aware orchestration around the compiled graph |
| `app/evaluation.py` | Auto-eval, dashboard, and annotation record builders |
| `app/api.py` | FastAPI application |
| `database/` | Supabase, Hive, and sync scripts |

## Requirements

- Python 3.10+
- `pip`
- No API key required for the default mock mode

## Installation

```bash
cd hxim-main
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## CLI Usage

Single-turn examples:

```bash
python scripts/run_chat.py --query "我的订单123456到哪了，帮我催一下"
python scripts/run_chat.py --query "订单778899漏发了，我要退款"
python scripts/run_chat.py --query "取消订单888888"
```

Interactive session:

```bash
python scripts/run_chat.py --interactive --session-id demo-session
```

Example conversation:

```text
我要退款
778899
确认
```

Cancellation confirmation:

```text
取消订单888888
确认
```

Cancel a pending mutation:

```text
取消订单888888
取消
```

## API Usage

Start the server:

```bash
uvicorn app.api:app --reload --port 8000
```

Send a chat message:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"query":"我的订单123456到哪了，帮我催一下","session_id":"demo-api","user_id":"demo-user"}'
```

Reset a session:

```bash
curl -X POST http://127.0.0.1:8000/reset/demo-api
```

List demo orders:

```bash
curl http://127.0.0.1:8000/demo/orders
```

Response fields for `POST /chat`:

| Field | Description |
| --- | --- |
| `reply` | Final user-facing response |
| `intent` | Detected intent |
| `route` | Router decision: `KNOWLEDGE`, `ACTION`, `HYBRID`, `ESCALATE`, or `CHITCHAT` |
| `escalate` | Whether the conversation should be transferred to a human |
| `trace` | Node-level execution trace |
| `session` | Session snapshot after the turn |
| `autoeval` | Auto-evaluation payload |
| `board_record` | Dashboard-compatible record |
| `annotation_record` | Annotation-compatible record |

## Demo Data

| Order ID | Status | Scenario | Example |
| --- | --- | --- | --- |
| `123456` | `delivering` | Delivery status and rush order | `我的订单123456到哪了，帮我催一下` |
| `888888` | `preparing` | Cancelable order | `取消订单888888` |
| `778899` | `delivered` | Refund or after-sale flow | `订单778899漏发了，我要退款` |

## Tests

```bash
.venv/bin/python -m pytest -q tests
```

Current coverage includes:

- Domain normalization, intent detection, and slot extraction.
- Declarative config loading and action-sequence validation.
- Single-turn LangGraph execution.
- Missing-slot continuation across turns.
- Session isolation and reset behavior.
- Food-safety escalation.
- Confirmation and cancellation of pending mutations.
- Self-built test orders for blocked refunds, unknown orders, and parallel pending confirmations.
- Evaluation payload consistency.

## Configuration

Environment variables are optional in mock mode.

| Variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `hxim-main` | FastAPI application name |
| `MOCK_MODE` | `true` | Reserved mock-mode switch |
| `MAX_AGENT_LOOP_ITERATIONS` | `3` | Maximum number of action results kept per turn |
| `DEFAULT_USER_ID` | `demo-user` | Default CLI/API user id |
| `DEFAULT_SESSION_ID` | `demo-session` | Default CLI/API session id |
| `DEFAULT_WM_POI_ID` | `100000` | Default merchant id for evaluation records without an order |

## Repository Structure

```text
hxim-main/
├── app/
│   ├── agents/
│   ├── configs/
│   ├── data/
│   ├── domain/
│   ├── state/
│   ├── tools/
│   ├── api.py
│   ├── evaluation.py
│   ├── service.py
│   ├── session_store.py
│   └── settings.py
├── database/
│   ├── hive/
│   ├── supabase/
│   └── sync/
├── docs/
├── scripts/
├── tests/
├── requirements.txt
└── README.md
```

## Limitations

- The Router is rule-based and does not use an LLM.
- Knowledge retrieval uses in-memory snippets rather than a vector database.
- Business actions operate on an in-memory mock database.
- Session state is process-local and is not durable across process restarts.
- Evaluation records are generated in memory; persistence is handled separately by database scripts.

## Related Docs

- [Repository Changelog](../CHANGELOG.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Progress Log](docs/PROGRESS_LOG.md)
- [Release Process](docs/RELEASE_PROCESS.md)
- [Database](database/README.md)

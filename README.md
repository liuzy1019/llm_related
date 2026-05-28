# llm_related

Collection of runnable examples, engineering prototypes, and study notes for large language models and AI agents.

The repository is organized as multiple independent subprojects. Each subproject maintains its own README, dependency file, scripts, and test suite when applicable.

## Repository Layout

```text
llm_related-main/
├── langgraph-scaffold/   # LangGraph agent scaffold and pattern examples
├── hxim-main/            # Offline customer-service agent prototype
├── rl-main/              # RL / RLHF / reasoning notebooks for LLMs
├── llm_pretrain/         # From-scratch LLM pretraining notes and skeleton
├── README.md
└── LICENSE
```

## Projects

| Project | Category | Description | Status |
| --- | --- | --- | --- |
| [langgraph-scaffold](langgraph-scaffold/) | Agent framework | LangGraph scaffold covering ReAct, Plan-and-Execute, Multi-Agent workflows, checkpointers, tool nodes, and tests. | Runnable |
| [hxim-main](hxim-main/) | Agent application | Offline food-delivery customer-service agent with declarative routing config, mock order actions, multi-turn state, confirmation flow, FastAPI, and evaluation payload adapters. | Runnable |
| [rl-main](rl-main/) | Research notes | Notebook collection for RL, RLHF, GRPO, reasoning, vLLM, SGLang, Ray, verl, and agent RL. | Notebook-based |
| [llm_pretrain](llm_pretrain/) | Training reproduction | Notes and project skeleton for tokenizer training, Megatron-LM pretraining, HuggingFace conversion, and Verl SFT. | Skeleton |

## Quick Start

### hxim-main

```bash
cd hxim-main
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/run_chat.py --query "我的订单123456到哪了，帮我催一下"
.venv/bin/python -m pytest -q tests
```

Start the API server:

```bash
uvicorn app.api:app --reload --port 8000
```

### langgraph-scaffold

```bash
cd langgraph-scaffold
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

MOCK_LLM=1 python scripts/run_agent.py --mode react --query "计算 123 * 456"
pytest -q
```

### rl-main

```bash
cd rl-main
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

## Development Notes

- Subprojects are intentionally decoupled. Run commands from the corresponding subproject directory unless stated otherwise.
- Application projects should keep an offline/mock path runnable for tests and demos.
- Large generated artifacts are not tracked: model weights, checkpoints, raw datasets, logs, caches, and local databases.
- Secrets and local configuration files are not tracked: `.env`, tokens, credentials, and private notes.
- GPU-heavy notebooks and training scripts may require CUDA, Linux, distributed runtime dependencies, or external model/data access.

## Documentation

- [Changelog](CHANGELOG.md)
- [langgraph-scaffold README](langgraph-scaffold/README.md)
- [hxim-main README](hxim-main/README.md)
- [hxim-main architecture](hxim-main/docs/ARCHITECTURE.md)
- [rl-main README](rl-main/README.md)
- [llm_pretrain README](llm_pretrain/README.md)

## License

See [LICENSE](LICENSE). Third-party frameworks, articles, datasets, and models referenced by subprojects remain subject to their own licenses and usage terms.

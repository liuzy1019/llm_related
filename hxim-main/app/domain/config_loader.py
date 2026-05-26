"""Load declarative runtime configuration for the customer-service demo."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.im_standards import IM_INTENTS

CONFIG_DIR = Path(__file__).resolve().parents[1] / "configs"


class ConfigError(ValueError):
    """Raised when declarative runtime config is invalid."""


@lru_cache(maxsize=1)
def load_intent_config() -> dict[str, Any]:
    config = _load_json("intents.json")
    intents = config.get("intents")
    if not isinstance(intents, list):
        raise ConfigError("intents.json must contain an intents list")

    seen: set[str] = set()
    for index, item in enumerate(intents):
        if not isinstance(item, dict):
            raise ConfigError(f"intent item #{index} must be an object")
        name = _require_str(item, "name", f"intent item #{index}")
        _require_str(item, "stage", f"intent {name}")
        _require_str(item, "route", f"intent {name}")
        confidence = item.get("confidence")
        if not isinstance(confidence, int | float):
            raise ConfigError(f"intent {name} must define numeric confidence")
        keywords = item.get("keywords")
        if not isinstance(keywords, list) or not all(isinstance(word, str) for word in keywords):
            raise ConfigError(f"intent {name} must define keywords as a string list")
        seen.add(name)

    missing = set(IM_INTENTS) - seen
    if missing:
        raise ConfigError("intents.json missing standard intents: " + ", ".join(sorted(missing)))
    return config


@lru_cache(maxsize=1)
def load_function_config() -> dict[str, Any]:
    config = _load_json("functions.json")
    functions = config.get("functions")
    if not isinstance(functions, dict):
        raise ConfigError("functions.json must contain a functions object")
    for name, metadata in functions.items():
        if not isinstance(metadata, dict):
            raise ConfigError(f"function {name} metadata must be an object")
        required_slots = metadata.get("required_slots")
        if not isinstance(required_slots, list) or not all(
            isinstance(slot, str) for slot in required_slots
        ):
            raise ConfigError(f"function {name} must define required_slots as a string list")

    action_sequences = config.get("action_sequences")
    if not isinstance(action_sequences, dict):
        raise ConfigError("functions.json must contain an action_sequences object")
    for intent, actions in action_sequences.items():
        if intent not in IM_INTENTS:
            raise ConfigError(f"unknown intent in action_sequences: {intent}")
        _validate_actions(actions, functions, f"action sequence for {intent}")

    default_actions = config.get("default_actions")
    _validate_actions(default_actions, functions, "default_actions")

    overrides = config.get("slot_overrides", [])
    if not isinstance(overrides, list):
        raise ConfigError("slot_overrides must be a list")
    for index, override in enumerate(overrides):
        if not isinstance(override, dict):
            raise ConfigError(f"slot override #{index} must be an object")
        _require_str(override, "slot", f"slot override #{index}")
        if "value" not in override:
            raise ConfigError(f"slot override #{index} must define value")
        intents = override.get("intents")
        if not isinstance(intents, list) or not all(intent in IM_INTENTS for intent in intents):
            raise ConfigError(f"slot override #{index} must define known intents")
        _validate_actions(override.get("actions"), functions, f"slot override #{index}")
    return config


@lru_cache(maxsize=1)
def load_sop_config() -> dict[str, Any]:
    config = _load_json("sop.json")
    for section in ("generator", "escalation", "chitchat"):
        if not isinstance(config.get(section), dict):
            raise ConfigError(f"sop.json must contain a {section} object")
    return config


def iter_intent_rules() -> tuple[dict[str, Any], ...]:
    return tuple(load_intent_config()["intents"])


def get_intent_rule(intent: str) -> dict[str, Any] | None:
    for item in iter_intent_rules():
        if item["name"] == intent:
            return item
    return None


def get_default_intent() -> str:
    return str(load_intent_config().get("default_intent", "澄清"))


def get_default_confidence() -> float:
    return float(load_intent_config().get("default_confidence", 0.62))


def get_action_sequence(intent: str, slots: dict[str, Any]) -> tuple[str, ...]:
    config = load_function_config()
    for override in config.get("slot_overrides", []):
        if (
            intent in override.get("intents", [])
            and slots.get(override["slot"]) == override.get("value")
        ):
            return tuple(override["actions"])
    actions = config["action_sequences"].get(intent, config["default_actions"])
    return tuple(actions)


def get_sop_text(section: str, key: str, default: str = "") -> str:
    value = load_sop_config().get(section, {}).get(key, default)
    return str(value)


def _load_json(filename: str) -> dict[str, Any]:
    path = CONFIG_DIR / filename
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except OSError as exc:
        raise ConfigError(f"cannot read config file {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{filename} must contain a JSON object")
    return data


def _require_str(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{context} must define non-empty string field {key}")
    return value


def _validate_actions(actions: Any, functions: dict[str, Any], context: str) -> None:
    if not isinstance(actions, list) or not actions:
        raise ConfigError(f"{context} must be a non-empty action list")
    unknown = [action for action in actions if action not in functions]
    if unknown:
        raise ConfigError(f"{context} references unknown functions: {', '.join(unknown)}")

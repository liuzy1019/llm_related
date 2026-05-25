"""Shared IM data standards from IM_autoeval and IM_board.

This module is the single source for runtime field names that must line up with
the imported evaluation/dashboard projects under ``docs/IM``.
"""

from __future__ import annotations

import json
import zlib
from datetime import datetime, timezone
from typing import Any

IM_INTENTS: tuple[str, ...] = (
    "退款",
    "修改订单",
    "备注",
    "少送错送",
    "食安",
    "餐损撒漏",
    "餐品不符合预期",
    "催单",
    "配送",
    "商品",
    "门店",
    "优惠",
    "团餐",
    "赠品",
    "发票",
    "转人工",
    "闲聊",
    "澄清",
)

BOARD_FIELDS: tuple[str, ...] = (
    "id",
    "session_id",
    "im_session_id",
    "date",
    "wm_poi_id",
    "user_id",
    "intent",
    "is_accurate",
    "inaccuracy_reason",
    "is_resolved",
    "create_time",
    "update_time",
    "session_data_string",
    "evaluation_workflow_version",
    "is_resolved_label",
    "is_accurate_label",
    "dt",
)

ANNOTATION_FIELDS: tuple[str, ...] = (
    "hive_id",
    "session_id",
    "im_session_id",
    "date",
    "wm_poi_id",
    "user_id",
    "session_data_string",
    "intent",
    "inaccuracy_reason",
    "is_resolved",
    "is_accurate",
    "create_time",
    "update_time",
    "evaluation_workflow_version",
    "is_resolved_label",
    "is_accurate_label",
    "dt",
)

AUTOEVAL_INPUT_FIELDS: tuple[str, ...] = (
    "querys",
    "historys",
    "wmPoiId",
    "messageType",
    "orderinfo",
    "imagemessage",
)

AUTOEVAL_OUTPUT_FIELDS: tuple[str, ...] = (
    "intent",
    "response",
    "botOutput",
    "ModelOut",
    "decisionData",
    "problemSolved",
    "toHuman",
    "__sys_aibox_llm_result_code",
    "任务状态",
)


def format_board_intent(intent: str) -> str:
    """Format a standard Chinese intent for the IM_board intent column."""
    return f"【{intent}】"


def now_shanghai_like() -> tuple[datetime, str, str, int]:
    """Return current timestamp pieces used by board/autoeval skeletons.

    Board/Hive query by yyyyMMdd ``date``/``dt`` and store create/update as
    Hive timestamps. The Java evaluator internally keeps epoch milliseconds,
    then writes JDBC timestamps, so the portable runtime record uses a timestamp
    text that Spark can parse with ``to_timestamp``.
    """
    now = datetime.now(timezone.utc).astimezone()
    date = now.strftime("%Y%m%d")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    epoch_ms = int(now.timestamp() * 1000)
    return now, date, timestamp, epoch_ms


def stable_hive_id(session_id: str, update_time_ms: int) -> int:
    """Generate a small positive bigint-compatible evaluation id for demos."""
    seed = f"{session_id}:{update_time_ms}".encode("utf-8")
    return zlib.crc32(seed) & 0x7FFFFFFF


def to_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

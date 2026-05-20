"""数据查询工具（示例：内存里的用户表）。"""

from __future__ import annotations

from langchain_core.tools import tool

_FAKE_USERS = {
    "1001": {"name": "张三", "team": "数立方", "role": "工程师"},
    "1002": {"name": "李四", "team": "AI Lab", "role": "研究员"},
}


@tool
def query_user(user_id: str) -> str:
    """根据 user_id 查询用户基本信息。"""
    try:
        u = _FAKE_USERS.get(user_id)
        if not u:
            return f"用户 {user_id} 不存在"
        return f"{u['name']} - {u['team']} - {u['role']}"
    except Exception as e:  # noqa: BLE001
        return f"query_user 调用失败: {e}"

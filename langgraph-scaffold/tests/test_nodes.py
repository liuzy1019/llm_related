"""节点 / 工具 单元测试

文章原话：
> ✅ 单元测试：每个节点函数独立测试
"""

from __future__ import annotations

from app.tools.code_tools import calculate
from app.tools.data_tools import query_user
from app.tools.file_tools import type_in_current_file
from app.tools.search_tools import search_weather


def test_calculate_basic():
    # @tool 装饰后通过 .invoke({...}) 触发
    assert calculate.invoke({"expression": "1+2*3"}) == "7"


def test_calculate_rejects_unsafe():
    out = calculate.invoke({"expression": "__import__('os').system('echo hi')"})
    assert "计算错误" in out


def test_search_weather_known_city():
    out = search_weather.invoke({"city": "北京"})
    assert "晴" in out


def test_search_weather_unknown_city():
    out = search_weather.invoke({"city": "火星"})
    assert "暂无数据" in out


def test_query_user_existing():
    assert "张三" in query_user.invoke({"user_id": "1001"})


def test_query_user_missing():
    assert "不存在" in query_user.invoke({"user_id": "9999"})


def test_type_in_current_file_appends_text(tmp_path, monkeypatch):
    target = tmp_path / "current.txt"
    target.write_text("hello", encoding="utf-8")
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("AGENT_CURRENT_FILE", str(target))

    out = type_in_current_file.invoke({"text": "\nworld"})

    assert "已向当前文件追加" in out
    assert target.read_text(encoding="utf-8") == "hello\nworld"


def test_type_in_current_file_rejects_outside_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("", encoding="utf-8")
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_CURRENT_FILE", str(target))

    out = type_in_current_file.invoke({"text": "nope"})

    assert "写入失败" in out
    assert target.read_text(encoding="utf-8") == ""

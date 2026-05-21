"""图集成测试 —— 完整跑一遍三种 Agent

依赖 Mock LLM（conftest.py 中已强制 MOCK_LLM=1），无需任何 API Key。
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.agents import build_multi_agent_graph, build_plan_execute_graph, build_react_graph
from app.checkpointers import get_checkpointer


def test_react_e2e_weather_and_calc():
    builder = build_react_graph()
    with get_checkpointer() as cp:
        graph = builder.compile(checkpointer=cp)
        result = graph.invoke(
            {
                "messages": [HumanMessage(content="北京今天天气怎么样？顺便算一下 12*8")],
                "iteration_count": 0,
            },
            config={"configurable": {"thread_id": "ut-react"}},
        )

    final = result["messages"][-1].content
    # Mock LLM 在收到工具结果后会输出 summary，应包含工具名或结果
    assert "search_weather" in final or "晴" in final
    assert "calculate" in final or "96" in final


def test_react_iteration_count_protected():
    """验证迭代计数器在状态中被正确累加（防无限循环）。"""
    builder = build_react_graph()
    with get_checkpointer() as cp:
        graph = builder.compile(checkpointer=cp)
        result = graph.invoke(
            {
                "messages": [HumanMessage(content="北京天气")],
                "iteration_count": 0,
            },
            config={"configurable": {"thread_id": "ut-react-iter"}},
        )
    assert result.get("iteration_count", 0) >= 1


def test_plan_execute_e2e_weather_and_calc():
    builder = build_plan_execute_graph()
    with get_checkpointer() as cp:
        graph = builder.compile(checkpointer=cp)
        result = graph.invoke(
            {"input": "查一下深圳天气并计算 88*99，最后告诉我结论"},
            config={"configurable": {"thread_id": "ut-plan-execute"}},
        )

    final = result["response"]
    assert "search_weather" in final or "小雨" in final
    assert "calculate" in final or "8712" in final


def test_multi_agent_e2e_weather_and_calc():
    builder = build_multi_agent_graph()
    with get_checkpointer() as cp:
        graph = builder.compile(checkpointer=cp)
        result = graph.invoke(
            {
                "messages": [HumanMessage(content="帮我查一下杭州的天气，并算 1+2+3+4+5")],
                "iteration_count": 0,
            },
            config={"configurable": {"thread_id": "ut-multi"}},
        )

    final = result["messages"][-1].content
    assert "search_weather" in final or "杭州" in final or "22" in final
    assert "calculate" in final or "15" in final


def test_react_e2e_type_in_current_file(tmp_path, monkeypatch):
    target = tmp_path / "current.txt"
    target.write_text("start", encoding="utf-8")
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("AGENT_CURRENT_FILE", str(target))

    builder = build_react_graph()
    with get_checkpointer() as cp:
        graph = builder.compile(checkpointer=cp)
        result = graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=(
                            f"当前文件路径：{target}\n"
                            "请在当前文件键入 `\nadded by agent`"
                        )
                    )
                ],
                "iteration_count": 0,
            },
            config={"configurable": {"thread_id": "ut-react-current-file"}},
        )

    final = result["messages"][-1].content
    assert "type_in_current_file" in final or "已向当前文件追加" in final
    assert target.read_text(encoding="utf-8") == "start\nadded by agent"

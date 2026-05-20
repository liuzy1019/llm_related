"""图集成测试 —— 完整跑一遍三种 Agent

依赖 Mock LLM（conftest.py 中已强制 MOCK_LLM=1），无需任何 API Key。
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from app.agents import build_react_graph
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

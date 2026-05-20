"""LLM 工厂：根据配置返回真实 ChatOpenAI 或离线 Mock LLM

- 设置 MOCK_LLM=1 时使用 MockChatLLM（无需任何 API Key 即可跑通流程）。
- MockChatLLM 仅做最小可用的工具调用模拟，足以让 ReAct/Plan-Execute 图正常流转。
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Iterable, List, Optional, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from .settings import settings


# --------------------------------------------------------------------------- #
# Mock LLM —— 用于离线/CI 跑通流程
# --------------------------------------------------------------------------- #
class MockChatLLM(BaseChatModel):
    """一个极简 Mock LLM。

    行为：
    - 第一次被调用时，如果 messages 中提到 "天气" 则发起 search_weather 工具调用，
      若提到数字算式（含 *、+、- 等）则发起 calculate 工具调用。
    - 如果 messages 中已经包含 ToolMessage，则视为"工具结果已就位"，输出最终答案。
    - 不依赖任何外网。
    """

    bound_tools: List[Any] = []

    @property
    def _llm_type(self) -> str:  # pragma: no cover - 框架要求
        return "mock-chat"

    # 兼容 LangChain 的 bind_tools 接口
    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "MockChatLLM":  # type: ignore[override]
        new = MockChatLLM()
        new.bound_tools = list(tools)
        return new

    # 兼容 with_structured_output（Plan/Replan 使用）
    def with_structured_output(self, schema: Any, **kwargs: Any) -> "_StructuredMock":
        return _StructuredMock(schema)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        # 已经收到工具结果 -> 输出终止答案
        if any(getattr(m, "type", "") == "tool" for m in messages):
            content = self._summarize_tool_results(messages)
            ai = AIMessage(content=content)
            return ChatResult(generations=[ChatGeneration(message=ai)])

        text = "\n".join(getattr(m, "content", "") or "" for m in messages)

        tool_calls = []
        weather_match = re.search(r"(北京|上海|深圳|广州|杭州|成都|纽约|东京)", text)
        calc_match = re.search(r"(\d+\s*[\*\+\-/x]\s*\d+(?:\s*[\*\+\-/x]\s*\d+)*)", text)

        if weather_match and self._has_tool("search_weather"):
            tool_calls.append(
                {
                    "name": "search_weather",
                    "args": {"city": weather_match.group(1)},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                }
            )
        if calc_match and self._has_tool("calculate"):
            tool_calls.append(
                {
                    "name": "calculate",
                    "args": {"expression": calc_match.group(1).replace("x", "*")},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                }
            )

        if tool_calls:
            ai = AIMessage(content="", tool_calls=tool_calls)
        else:
            ai = AIMessage(content="(mock) 我已尽力理解，但未触发工具调用。")
        return ChatResult(generations=[ChatGeneration(message=ai)])

    # --- helpers ---
    def _has_tool(self, name: str) -> bool:
        for t in self.bound_tools:
            tname = getattr(t, "name", None) or getattr(t, "__name__", "")
            if tname == name:
                return True
        return False

    @staticmethod
    def _summarize_tool_results(messages: Iterable[BaseMessage]) -> str:
        results = [
            f"- {getattr(m, 'name', '?')}: {m.content}"
            for m in messages
            if getattr(m, "type", "") == "tool"
        ]
        return "(mock) 工具调用已完成，结果如下：\n" + "\n".join(results)


class _StructuredMock:
    """模拟 with_structured_output：返回符合 schema 的最简对象。"""

    def __init__(self, schema: Any) -> None:
        self.schema = schema

    def invoke(self, payload: Any, **kwargs: Any) -> Any:
        # 兼容 Plan / Act / Response：只输出最简单的结构
        schema_name = getattr(self.schema, "__name__", "")
        if schema_name == "Plan":
            return self.schema(steps=["收集所需信息", "整合并给出最终答案"])
        if schema_name == "Act":
            # 直接给出 Response 终止
            from app.agents.plan_execute_agent import Response  # 延迟导入避免循环

            return self.schema(action=Response(response="(mock) 已根据计划完成所有步骤。"))
        if schema_name == "Response":
            return self.schema(response="(mock) ok")
        # 兜底
        try:
            return self.schema()
        except Exception:
            return self.schema(steps=["mock-step"])  # type: ignore[call-arg]


# --------------------------------------------------------------------------- #
# 工厂函数
# --------------------------------------------------------------------------- #
def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """返回当前生效的 LLM。"""
    if settings.mock_llm or not settings.openai_api_key or settings.openai_api_key.startswith("sk-replace"):
        return MockChatLLM()

    # 真实 OpenAI（需要联网 & 有效 Key）
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.openai_model,
        temperature=temperature,
        api_key=settings.openai_api_key,
    )

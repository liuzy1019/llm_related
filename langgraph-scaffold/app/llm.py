"""LLM 工厂：根据配置返回真实 ChatOpenAI 或离线 Mock LLM

- 设置 MOCK_LLM=1 时使用 MockChatLLM（无需任何 API Key 即可跑通流程）。
- MockChatLLM 仅做最小可用的工具调用模拟，足以让 ReAct/Plan-Execute 图正常流转。
"""

from __future__ import annotations

import ast
import re
import uuid
from typing import Any, Iterable, List, Optional, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable

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
        # LangChain 的真实模型会返回一个“绑定工具后的模型对象”。
        # Mock 这里也返回一个新实例，避免不同 agent 之间共享 bound_tools。
        new = MockChatLLM()
        new.bound_tools = list(tools)
        return new

    # 兼容 with_structured_output（Plan/Replan 使用）
    def with_structured_output(self, schema: Any, **kwargs: Any) -> "_StructuredMock":
        # 真实 LLM 会按 Pydantic schema 输出结构化对象；Mock 用规则模拟。
        return _StructuredMock(schema)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        # 已经收到当前绑定工具的结果 -> 输出终止答案。
        # Multi-Agent 场景下不同 worker 共享消息历史，因此要忽略其他 worker 的工具结果。
        relevant_tool_names = self._bound_tool_names()
        has_relevant_tool_result = any(
            getattr(m, "type", "") == "tool"
            and (not relevant_tool_names or getattr(m, "name", "") in relevant_tool_names)
            for m in messages
        )
        if has_relevant_tool_result:
            content = self._summarize_tool_results(messages)
            ai = AIMessage(content=content)
            return ChatResult(generations=[ChatGeneration(message=ai)])

        # 第一次调用时从用户文本里提取“城市”和“算式”，用来伪造工具调用。
        text = "\n".join(getattr(m, "content", "") or "" for m in messages)

        tool_calls = []
        weather_match = re.search(r"(北京|上海|深圳|广州|杭州|成都|纽约|东京)", text)
        calc_match = re.search(r"(\d+\s*[\*\+\-/x]\s*\d+(?:\s*[\*\+\-/x]\s*\d+)*)", text)
        file_write_text = self._extract_current_file_text(text)

        if weather_match and self._has_tool("search_weather"):
            tool_calls.append(
                {
                    "name": "search_weather",
                    "args": {"city": weather_match.group(1)},
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                }
            )
        if file_write_text and self._has_tool("type_in_current_file"):
            tool_calls.append(
                {
                    "name": "type_in_current_file",
                    "args": {"text": file_write_text},
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
            # AIMessage.tool_calls 是 ToolNode 识别并执行工具的关键字段。
            ai = AIMessage(content="", tool_calls=tool_calls)
        else:
            ai = AIMessage(content="(mock) 我已尽力理解，但未触发工具调用。")
        return ChatResult(generations=[ChatGeneration(message=ai)])

    # --- helpers ---
    def _has_tool(self, name: str) -> bool:
        return name in self._bound_tool_names()

    def _bound_tool_names(self) -> set[str]:
        return {
            getattr(t, "name", None) or getattr(t, "__name__", "")
            for t in self.bound_tools
        }

    @staticmethod
    def _summarize_tool_results(messages: Iterable[BaseMessage]) -> str:
        results = [
            f"- {getattr(m, 'name', '?')}: {m.content}"
            for m in messages
            if getattr(m, "type", "") == "tool"
        ]
        return "(mock) 工具调用已完成，结果如下：\n" + "\n".join(results)

    @staticmethod
    def _extract_current_file_text(text: str) -> str | None:
        """从“在当前文件键入/写入...”这类中文指令中提取要写入的文本。"""
        task_text = text.split("用户任务：", 1)[-1]
        if "当前文件" not in task_text:
            return None
        if not any(kw in task_text for kw in ("键入", "写入", "追加", "输入")):
            return None

        quoted = re.search(r"[`'\"]([^`'\"]+)[`'\"]", task_text)
        if quoted:
            return quoted.group(1)
        chinese_quoted = re.search(r"[“「『]([^”」』]+)[”」』]", task_text)
        if chinese_quoted:
            return chinese_quoted.group(1)
        tail = re.search(r"(?:键入|写入|追加|输入)\s*[:：]?\s*(.+)$", task_text, flags=re.S)
        if tail:
            return tail.group(1).strip()
        return None


class _StructuredMock(Runnable[Any, Any]):
    """模拟 with_structured_output：返回符合 schema 的最简对象。

    这个类继承 Runnable，是为了能参与 LCEL 管道：prompt | structured_llm。
    """

    def __init__(self, schema: Any) -> None:
        self.schema = schema

    def invoke(self, payload: Any, config: Any = None, **kwargs: Any) -> Any:
        # payload 可能是 prompt value、dict 或字符串，先统一拉平成文本。
        text = self._payload_text(payload)
        schema_name = getattr(self.schema, "__name__", "")
        if schema_name == "Plan":
            return self.schema(steps=self._make_plan_steps(text))
        if schema_name == "Act":
            # Act 用于 Replanner：还有剩余步骤就继续，否则输出最终 Response。
            remaining = self._remaining_steps(text)
            if remaining:
                from app.agents.plan_execute_agent import Plan  # 延迟导入避免循环

                return self.schema(action=Plan(steps=remaining))
            from app.agents.plan_execute_agent import Response  # 延迟导入避免循环

            return self.schema(action=Response(response=self._make_response(text)))
        if schema_name == "Response":
            return self.schema(response="(mock) ok")
        # 兜底
        try:
            return self.schema()
        except Exception:
            return self.schema(steps=["mock-step"])  # type: ignore[call-arg]

    @staticmethod
    def _payload_text(payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if hasattr(payload, "to_messages"):
            return "\n".join(str(getattr(m, "content", "")) for m in payload.to_messages())
        if isinstance(payload, dict):
            return "\n".join(str(v) for v in payload.values())
        return str(payload)

    @staticmethod
    def _make_plan_steps(text: str) -> List[str]:
        """从目标文本中构造可执行计划；仅用于离线演示和测试。"""
        steps: List[str] = []
        file_write_text = MockChatLLM._extract_current_file_text(text)
        if file_write_text:
            steps.append(f"在当前文件键入 `{file_write_text}`")
        city_match = re.search(r"(北京|上海|深圳|广州|杭州|成都|纽约|东京)", text)
        if city_match and "天气" in text:
            steps.append(f"查询{city_match.group(1)}天气")
        calc_match = re.search(r"(\d+\s*[\*\+\-/x]\s*\d+(?:\s*[\*\+\-/x]\s*\d+)*)", text)
        if calc_match:
            steps.append(f"计算 {calc_match.group(1).replace('x', '*')}")
        return steps or ["收集所需信息"]

    @staticmethod
    def _remaining_steps(text: str) -> List[str]:
        """根据 replanner prompt 中的原计划/已完成记录，计算剩余步骤。"""
        plan = _StructuredMock._literal_after_label(text, "原计划") or []
        past_steps = _StructuredMock._literal_after_label(text, "已完成") or []
        completed = {step for step, _ in past_steps if isinstance(step, str)}
        return [step for step in plan if step not in completed]

    @staticmethod
    def _make_response(text: str) -> str:
        past_steps = _StructuredMock._literal_after_label(text, "已完成") or []
        if not past_steps:
            return "(mock) 已根据计划完成所有步骤。"
        lines = [f"- {step}: {result}" for step, result in past_steps]
        return "(mock) 已根据计划完成所有步骤，结果如下：\n" + "\n".join(lines)

    @staticmethod
    def _literal_after_label(text: str, label: str) -> Any:
        """从中文 prompt 的某个标签后解析 Python 字面量列表。"""
        match = re.search(rf"{label}：(.*?)(?:\n\S+：|\Z)", text, flags=re.S)
        if not match:
            return None
        try:
            return ast.literal_eval(match.group(1).strip())
        except Exception:
            return None


# --------------------------------------------------------------------------- #
# 工厂函数
# --------------------------------------------------------------------------- #
def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """返回当前生效的 LLM。"""
    # 没有 key 时自动走 Mock，保证 README 示例和 CI 在离线环境也能跑。
    if settings.mock_llm or not settings.openai_api_key or settings.openai_api_key.startswith("sk-replace"):
        return MockChatLLM()

    # 真实 OpenAI（需要联网 & 有效 Key）
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.openai_model,
        temperature=temperature,
        api_key=settings.openai_api_key,
    )

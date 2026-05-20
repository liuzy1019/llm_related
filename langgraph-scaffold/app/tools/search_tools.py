"""搜索类工具

文章中给的示例工具——返回 mock 数据。生产环境替换为真实 API（如 SerpAPI、Tavily）即可。
所有工具都遵循 "异常必须捕获并返回字符串" 的最佳实践，避免一次调用失败导致整张图崩溃。
"""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def search_weather(city: str) -> str:
    """查询指定城市的实时天气。"""
    try:
        # demo: 真实场景请改为调用 OpenWeather / 心知天气等 API
        fake_db = {
            "北京": "晴，15°C，湿度 60%",
            "上海": "多云，20°C，湿度 70%",
            "深圳": "小雨，26°C，湿度 85%",
            "广州": "阴，27°C，湿度 80%",
            "杭州": "晴，22°C，湿度 65%",
            "成都": "多云，18°C，湿度 75%",
        }
        return fake_db.get(city, f"{city} 暂无数据（mock）")
    except Exception as e:  # noqa: BLE001
        return f"search_weather 调用失败: {e}"


@tool
def search_web(query: str) -> str:
    """搜索互联网，返回相关信息。"""
    try:
        return f"关于 '{query}' 的搜索结果（mock）：这里是网页摘要。"
    except Exception as e:  # noqa: BLE001
        return f"search_web 调用失败: {e}"

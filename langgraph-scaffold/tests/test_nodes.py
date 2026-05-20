"""节点 / 工具 单元测试

文章原话：
> ✅ 单元测试：每个节点函数独立测试
"""

from __future__ import annotations

from app.tools.code_tools import calculate
from app.tools.data_tools import query_user
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

"""代码 / 计算工具

文章 ReAct 示例里使用了 calculate(expression)。
注意：原文示例使用 eval()，生产环境 **强烈不建议**，这里改为 AST 安全求值版本。
"""

from __future__ import annotations

import ast
import operator as op

from langchain_core.tools import tool

# 仅放行的算术运算符
_ALLOWED_BIN_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.FloorDiv: op.floordiv,
}
_ALLOWED_UNARY_OPS = {ast.UAdd: op.pos, ast.USub: op.neg}


def _safe_eval(node: ast.AST) -> float:
    """递归求值 AST，仅支持数字与算术运算。"""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    # python<3.8 老节点，兼容
    if isinstance(node, ast.Num):  # type: ignore[attr-defined]
        return node.n  # type: ignore[attr-defined]
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN_OPS:
        return _ALLOWED_BIN_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPS:
        return _ALLOWED_UNARY_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"不允许的表达式节点：{type(node).__name__}")


@tool
def calculate(expression: str) -> str:
    """计算数学表达式，例如 '123*456'，仅支持 + - * / % ** //。"""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
        return str(result)
    except Exception as e:  # noqa: BLE001
        return f"计算错误: {e}"

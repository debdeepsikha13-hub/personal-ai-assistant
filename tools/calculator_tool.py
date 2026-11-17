"""
Safe Mathematical Calculator Tool.
==================================
Evaluates mathematical expressions safely using Python's math module and ast.

WHY THIS FOLDER MATTERS:
- Modify this file if you want to add support for symbolic calculus, units,
  numpy matrices, or financial calculations.
"""

import math
import ast
import operator
from langchain_core.tools import tool

# Supported safe operators
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "abs": abs,
    "round": round,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant): # numbers in python 3.8+
        return node.value
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in _SAFE_OPERATORS:
            return _SAFE_OPERATORS[op_type](_safe_eval(node.left), _safe_eval(node.right))
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in _SAFE_OPERATORS:
            return _SAFE_OPERATORS[op_type](_safe_eval(node.operand))
    elif isinstance(node, ast.Name):
        if node.id in _SAFE_FUNCTIONS:
            return _SAFE_FUNCTIONS[node.id]
    elif isinstance(node, ast.Call):
        func = _safe_eval(node.func)
        args = [_safe_eval(a) for a in node.args]
        if callable(func):
            return func(*args)
    raise ValueError(f"Unsupported or unsafe expression component: {ast.dump(node)}")


@tool
def calculate(expression: str) -> str:
    """
    Safely evaluate a mathematical calculation or formula.
    
    Args:
        expression: The math expression to compute (e.g. '125 * 4.5', '(45 + 10) / 2', 'sqrt(144) + 10', '2**8').
    
    Returns:
        The exact computed numeric result.
    """
    cleaned = expression.strip().replace("^", "**")
    try:
        parsed = ast.parse(cleaned, mode='eval')
        result = _safe_eval(parsed.body)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error calculating '{expression}': {str(e)}"


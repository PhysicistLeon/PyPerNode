from __future__ import annotations

import ast
import textwrap
from typing import Optional

from .node_types import NodeDefinition, SocketDef, ValueType


def _annotation_to_type(annotation: Optional[ast.expr]) -> ValueType:
    if isinstance(annotation, ast.Name):
        name = annotation.id.lower()
    elif isinstance(annotation, ast.Attribute):
        name = annotation.attr.lower()
    else:
        return ValueType.ANY

    if name in {"int", "float", "number"}:
        return ValueType.NUMBER
    if name in {"str", "string"}:
        return ValueType.STRING
    if name in {"bool", "boolean"}:
        return ValueType.BOOLEAN
    if name in {"date", "datetime"}:
        return ValueType.DATE
    return ValueType.ANY


def _default_value(node: ast.expr, fallback: ValueType):
    try:
        return ast.literal_eval(node)
    except Exception:
        return fallback.default_value()


def parse_function(code: str) -> NodeDefinition:
    """Interpret a Python function definition into a NodeDefinition."""

    cleaned_code = textwrap.dedent(code).strip()
    tree = ast.parse(cleaned_code)

    func_def = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            func_def = node
            break
    if func_def is None:
        raise ValueError("No function definition found in code block")

    inputs: list[SocketDef] = []
    total_args = func_def.args.args
    defaults = [None] * (len(total_args) - len(func_def.args.defaults)) + func_def.args.defaults

    for arg_node, default_node in zip(total_args, defaults):
        val_type = _annotation_to_type(arg_node.annotation)
        default = (
            _default_value(default_node, val_type)
            if default_node is not None
            else val_type.default_value()
        )
        inputs.append(SocketDef(arg_node.arg, val_type, default))

    return_type = _annotation_to_type(func_def.returns)
    outputs = [SocketDef("result", return_type)]

    return NodeDefinition(func_def.name, inputs, outputs, cleaned_code)

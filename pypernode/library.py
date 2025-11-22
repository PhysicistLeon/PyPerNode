from __future__ import annotations

from typing import Dict, List, Optional

from .interpreter import parse_function
from .node_types import NodeDefinition


DEFAULT_NODE_CODES = [
    """
def constant(value: float = 0.0) -> float:
    return value
""",
    """
def add(a: float, b: float) -> float:
    return a + b
""",
    """
def subtract(a: float, b: float) -> float:
    return a - b
""",
    """
def multiply(a: float, b: float) -> float:
    return a * b
""",
    """
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError('Division by zero')
    return a / b
""",
    """
def output(value) -> object:
    return value
""",
    """
def number_to_string(value: float) -> str:
    return str(value)
""",
    """
def string_to_number(text: str) -> float:
    return float(text)
""",
    """
def boolean_to_string(value: bool) -> str:
    return str(value)
""",
    """
def string_to_boolean(text: str) -> bool:
    return text.lower() in ('true', '1', 'yes')
""",
    """
from datetime import datetime, date


def string_to_date(text: str) -> date:
    return datetime.strptime(text, '%Y-%m-%d').date()
""",
    """
from datetime import date


def date_to_string(value: date) -> str:
    return value.isoformat()
""",
]


class NodeLibrary:
    _definitions: Dict[str, NodeDefinition] = {}

    @classmethod
    def register_from_code(cls, code: str) -> NodeDefinition:
        definition = parse_function(code)
        cls._definitions[definition.name] = definition
        return definition

    @classmethod
    def get_definition(cls, type_name: str) -> Optional[NodeDefinition]:
        return cls._definitions.get(type_name)

    @classmethod
    def get_all_definitions(cls) -> List[NodeDefinition]:
        return list(cls._definitions.values())

    @classmethod
    def register_default_nodes(cls) -> None:
        for code in DEFAULT_NODE_CODES:
            cls.register_from_code(code)

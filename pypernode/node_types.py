from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any


class ValueType(str, Enum):
    """Supported primitive value types for node inputs and outputs."""

    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    DATE = "date"
    ANY = "any"

    def default_value(self) -> Any:
        if self == ValueType.NUMBER:
            return 0.0
        if self == ValueType.STRING:
            return ""
        if self == ValueType.BOOLEAN:
            return False
        if self == ValueType.DATE:
            return date.today()
        return None

    def color(self):
        if self == ValueType.NUMBER:
            return "#FF7700"
        if self == ValueType.STRING:
            return "#00BFA6"
        if self == ValueType.BOOLEAN:
            return "#4CAF50"
        if self == ValueType.DATE:
            return "#3F51B5"
        return "#888888"

    def is_compatible_with(self, other: "ValueType") -> bool:
        if self == ValueType.ANY or other == ValueType.ANY:
            return True
        return self == other


@dataclass
class SocketDef:
    name: str
    type: ValueType
    default: Any = None


@dataclass
class NodeDefinition:
    name: str
    inputs: list[SocketDef]
    outputs: list[SocketDef]
    code: str

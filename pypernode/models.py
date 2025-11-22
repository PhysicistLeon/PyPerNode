import hashlib
import json
import time
from typing import Dict, Optional

from .interpreter import parse_function
from .node_types import NodeDefinition


class NodeData:
    def __init__(self, definition: NodeDefinition, x: float = 0, y: float = 0, id: Optional[str] = None):
        self.id = id if id else str(int(time.time() * 1000)) + str(id)
        self.x = x
        self.y = y

        self.definition = definition
        self.type = definition.name
        self.input_defs = definition.inputs
        self.output_defs = definition.outputs
        self.inputs = [i.name for i in self.input_defs]
        self.outputs = [o.name for o in self.output_defs]
        self.code = definition.code
        self.params = {sock.name: sock.default for sock in self.input_defs}

        # Runtime State
        self.last_output: Dict[str, object] = {}
        self.last_error: Optional[str] = None
        self.cache_hash: Optional[str] = None

    def refresh_definition_from_code(self) -> None:
        try:
            new_def = parse_function(self.code)
            self.definition = new_def
            self.type = new_def.name
            self.input_defs = new_def.inputs
            self.output_defs = new_def.outputs
            self.inputs = [i.name for i in self.input_defs]
            self.outputs = [o.name for o in self.output_defs]
            for sock in self.input_defs:
                self.params.setdefault(sock.name, sock.default)
        except Exception:
            # Keep previous definition if parsing fails
            pass

    def compute_hash(self, input_values: Dict[str, object]) -> str:
        hasher = hashlib.sha256()
        hasher.update(json.dumps(self.params, sort_keys=True, default=str).encode('utf-8'))
        hasher.update(self.code.encode('utf-8'))
        hasher.update(str(input_values).encode('utf-8'))
        return hasher.hexdigest()

    def execute(self, input_data: Dict[str, object]):
        local_scope: Dict[str, object] = {}
        exec(self.code, local_scope, local_scope)
        func = local_scope.get(self.definition.name)
        if not callable(func):
            raise ValueError(f"Function {self.definition.name} not found in code")
        result = func(**input_data)
        return {self.output_defs[0].name: result}

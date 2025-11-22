import hashlib
import json
import time
from typing import Dict, Optional

from .registry import NodeRegistry


class NodeData:
    def __init__(self, node_type: str, x: float = 0, y: float = 0, id: Optional[str] = None):
        self.id = id if id else str(int(time.time() * 1000)) + str(id)
        self.type = node_type
        self.x = x
        self.y = y

        defn = NodeRegistry.get_definition(node_type)
        if not defn:
            defn = {'inputs': [], 'outputs': [], 'code': 'pass', 'params': {}}

        self.inputs = defn['inputs'][:]
        self.outputs = defn['outputs'][:]
        self.code = defn['code']
        self.params = defn['params'].copy()

        # Runtime State
        self.last_output: Dict[str, object] = {}
        self.last_error: Optional[str] = None
        self.cache_hash: Optional[str] = None

    def compute_hash(self, input_values: Dict[str, object]) -> str:
        hasher = hashlib.sha256()
        hasher.update(json.dumps(self.params, sort_keys=True).encode('utf-8'))
        hasher.update(self.code.encode('utf-8'))
        hasher.update(str(input_values).encode('utf-8'))
        return hasher.hexdigest()

    def execute(self, input_data: Dict[str, object]):
        local_scope = {'inputs': input_data, 'outputs': {}, 'params': self.params}
        exec(self.code, {}, local_scope)
        return local_scope['outputs']

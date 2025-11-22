from typing import Dict, List, Optional


class NodeRegistry:
    _definitions: Dict[str, Dict[str, object]] = {}

    @classmethod
    def register_node(cls, type_name: str, inputs: List[str], outputs: List[str], code: str, params: Optional[Dict[str, object]] = None):
        cls._definitions[type_name] = {
            'inputs': inputs,
            'outputs': outputs,
            'code': code,
            'params': params or {},
        }

    @classmethod
    def get_definition(cls, type_name: str) -> Optional[Dict[str, object]]:
        return cls._definitions.get(type_name, None)

    @classmethod
    def get_all_types(cls) -> List[str]:
        return list(cls._definitions.keys())


def register_default_nodes() -> None:
    NodeRegistry.register_node(
        'Constant', [], ['Val'],
        code="outputs['Val'] = float(params['value'])",
        params={'value': 0.0},
    )

    NodeRegistry.register_node(
        'Add', ['A', 'B'], ['Result'],
        code="outputs['Result'] = inputs['A'] + inputs['B']",
    )

    NodeRegistry.register_node(
        'Subtract', ['A', 'B'], ['Result'],
        code="outputs['Result'] = inputs['A'] - inputs['B']",
    )

    NodeRegistry.register_node(
        'Multiply', ['A', 'B'], ['Result'],
        code="outputs['Result'] = inputs['A'] * inputs['B']",
    )

    NodeRegistry.register_node(
        'Divide', ['A', 'B'], ['Result'],
        code="if inputs['B'] == 0: raise ValueError('Div by Zero')\noutputs['Result'] = inputs['A'] / inputs['B']",
    )

    NodeRegistry.register_node(
        'Output', ['In'], [],
        code="pass # Data is simply cached",
    )

    NodeRegistry.register_node(
        'Custom', ['x', 'y'], ['out'],
        code="# Custom Python Code\nimport math\noutputs['out'] = math.sqrt(inputs['x']**2 + inputs['y']**2)",
    )

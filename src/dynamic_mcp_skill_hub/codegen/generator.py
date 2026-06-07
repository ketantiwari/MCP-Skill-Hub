from __future__ import annotations

from typing import Any

from dynamic_mcp_skill_hub.models import ToolSpec


def generate_schema(spec: ToolSpec) -> dict[str, Any]:
    return {
        "inputSchema": spec.inputs,
        "outputSchema": spec.outputs,
    }


def generate_test_cases(spec: ToolSpec) -> list[dict[str, Any]]:
    return [
        {
            "name": scenario.name,
            "input": scenario.input,
            "expected": scenario.expected,
        }
        for scenario in spec.test_scenarios
    ]


def generate_python_tool_code(spec: ToolSpec) -> str:
    tool_name = spec.name
    description = spec.description.replace("\"\"\"", "'")
    return f'''"""Auto-generated tool: {tool_name}

{description}
"""

from __future__ import annotations
from typing import Any


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    return {{
        "tool_name": "{tool_name}",
        "description": "{description}",
        "input": input_data,
        "status": "ok",
    }}
'''


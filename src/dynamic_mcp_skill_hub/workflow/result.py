from typing import Any, TypedDict

from dynamic_mcp_skill_hub.models import ToolSpec


class WorkflowResult(TypedDict, total=False):
    user_request: str
    intent: str
    spec: dict[str, Any]
    validation_passed: bool
    messages: list[str]
    tool_spec: ToolSpec


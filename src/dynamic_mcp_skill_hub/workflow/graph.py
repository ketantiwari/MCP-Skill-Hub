from typing import TypedDict

from dynamic_mcp_skill_hub.llm import ModelRequest, ModelRouter, extract_json_object
from dynamic_mcp_skill_hub.models import ToolIntent, ToolSpec
from dynamic_mcp_skill_hub.specs import normalize_tool_spec
from dynamic_mcp_skill_hub.research import TavilyResearchAdapter
from dynamic_mcp_skill_hub.validation import ToolValidator
from dynamic_mcp_skill_hub.workflow.result import WorkflowResult


class WorkflowState(TypedDict, total=False):
    user_request: str
    intent: ToolIntent
    spec: dict[str, object]
    validation_passed: bool
    messages: list[str]
    tool_spec: ToolSpec


class ToolCreationWorkflow:
    def __init__(
        self,
        model_router: ModelRouter | None = None,
        research: TavilyResearchAdapter | None = None,
        validator: ToolValidator | None = None,
    ) -> None:
        self.model_router = model_router or ModelRouter()
        self.research = research or TavilyResearchAdapter()
        self.validator = validator or ToolValidator()

    def run(self, user_request: str) -> WorkflowResult:
        state: WorkflowState = {"user_request": user_request, "messages": []}
        self._intake(state)
        self._spec_builder(state)
        self._research_if_needed(state)
        self._validate(state)
        result: WorkflowResult = {
            "user_request": state["user_request"],
            "intent": state["intent"],
            "spec": state["spec"],
            "validation_passed": state["validation_passed"],
            "messages": state["messages"],
        }
        if "tool_spec" in state:
            result["tool_spec"] = state["tool_spec"]
        return result

    def _intake(self, state: WorkflowState) -> None:
        normalized = state["user_request"].lower()
        if "rollback" in normalized:
            intent: ToolIntent = "rollback_tool"
        elif "execute" in normalized or "run" in normalized:
            intent = "execute_tool"
        elif "update" in normalized:
            intent = "update_tool"
        elif "version" in normalized:
            intent = "version_tool"
        else:
            intent = "create_tool"

        state["intent"] = intent
        state["messages"].append(f"Intent classified as {intent}.")

    def _spec_builder(self, state: WorkflowState) -> None:
        try:
            response = self.model_router.generate(
                ModelRequest(
                    system=(
                        "Create a strict JSON tool specification for a filesystem-based MCP tool. "
                        "Return only JSON with fields: name, description, tags, inputs, outputs, "
                        "side_effects, dependencies, permissions, safety_constraints, risk_level, "
                        "examples, test_scenarios, research_sources."
                    ),
                    prompt=state["user_request"],
                    json_mode=True,
                )
            )
            candidate = extract_json_object(response.text)
            state["tool_spec"] = normalize_tool_spec(candidate, state["user_request"])
            state["spec"] = state["tool_spec"].model_dump()
            state["messages"].append(f"Spec generated using {response.provider}.")
        except Exception as exc:
            state["messages"].append(f"Model generation fell back to placeholder spec: {exc}")

        if "tool_spec" not in state:
            state["tool_spec"] = ToolSpec.model_validate(
                {
                    "name": "generated_tool_placeholder",
                    "description": "Placeholder spec generated from the workflow skeleton.",
                    "tags": ["generated"],
                    "inputs": {"type": "object", "properties": {}},
                    "outputs": {"type": "object", "properties": {}},
                    "side_effects": [],
                    "dependencies": [],
                    "permissions": [],
                    "safety_constraints": ["Do not execute outside the configured sandbox."],
                    "risk_level": "low",
                    "examples": [{"input": {}, "output": {}}],
                    "test_scenarios": [{"name": "empty input", "input": {}, "expected": {}}],
                }
            )
            state["spec"] = state["tool_spec"].model_dump()
        state["messages"].append("Canonical tool spec created.")

    def _research_if_needed(self, state: WorkflowState) -> None:
        if "current" not in state["user_request"].lower():
            return

        sources = self.research.search(state["user_request"])
        state["spec"]["research_sources"] = [source.__dict__ for source in sources]
        state["messages"].append(f"Research attached with {len(sources)} source(s).")

    def _validate(self, state: WorkflowState) -> None:
        report = self.validator.validate_spec(state["spec"])
        state["validation_passed"] = report.passed
        state["messages"].append("Validation passed." if report.passed else "Validation failed.")

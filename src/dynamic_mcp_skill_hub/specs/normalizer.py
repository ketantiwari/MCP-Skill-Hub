from __future__ import annotations

import re
from typing import Any

from dynamic_mcp_skill_hub.models import ResearchSource, ToolDependency, ToolExample, ToolSpec, ToolTestScenario


def normalize_tool_spec(candidate: dict[str, Any], fallback_name: str) -> ToolSpec:
    normalized = {
        "name": _normalize_name(candidate.get("name") or fallback_name),
        "description": str(candidate.get("description") or fallback_name.replace("_", " ")),
        "tags": _string_list(candidate.get("tags") or []),
        "inputs": _normalize_schema(candidate.get("inputs") or candidate.get("input_schema") or {}),
        "outputs": _normalize_schema(candidate.get("outputs") or candidate.get("output_schema") or {}),
        "side_effects": _normalize_effects(candidate.get("side_effects") or candidate.get("sideEffects") or []),
        "dependencies": _normalize_dependencies(candidate.get("dependencies") or []),
        "permissions": _string_list(candidate.get("permissions") or []),
        "safety_constraints": _normalize_effects(
            candidate.get("safety_constraints") or candidate.get("safetyConstraints") or []
        ),
        "risk_level": _normalize_risk(candidate.get("risk_level") or candidate.get("riskLevel")),
        "examples": _normalize_examples(candidate.get("examples") or []),
        "test_scenarios": _normalize_test_scenarios(
            candidate.get("test_scenarios") or candidate.get("testScenarios") or []
        ),
        "research_sources": _normalize_sources(
            candidate.get("research_sources") or candidate.get("researchSources") or []
        ),
    }
    return ToolSpec.model_validate(normalized)


def _normalize_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "generated_tool"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if isinstance(item, str):
            items.append(item)
        elif isinstance(item, dict):
            text = item.get("name") or item.get("title") or item.get("description") or item.get("summary")
            if text:
                items.append(str(text))
    return items


def _normalize_effects(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            items.append(item)
        elif isinstance(item, dict):
            text = item.get("name") or item.get("description") or item.get("summary")
            if text:
                items.append(str(text))
    return items


def _normalize_schema(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, list):
        return {"type": "object", "properties": {}}

    properties: dict[str, Any] = {}
    required: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _normalize_name(item.get("name") or item.get("field") or item.get("key"))
        if not name:
            continue
        properties[name] = {
            "type": item.get("type", "string"),
            "description": item.get("description") or item.get("summary") or "",
        }
        if "default" in item:
            properties[name]["default"] = item["default"]
        if not item.get("optional", False):
            required.append(name)

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _normalize_dependencies(value: Any) -> list[ToolDependency]:
    if not isinstance(value, list):
        return []

    dependencies: list[ToolDependency] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("title") or item.get("package") or "").strip()
        if not name:
            continue
        dependencies.append(
            ToolDependency(
                name=name,
                version=str(item.get("version")) if item.get("version") else None,
                reason=str(
                    item.get("reason")
                    or item.get("description")
                    or item.get("summary")
                    or "Model-generated dependency"
                ),
                allowed=bool(item.get("allowed", True)),
            )
        )
    return dependencies


def _normalize_examples(value: Any) -> list[ToolExample]:
    if not isinstance(value, list):
        return []
    examples: list[ToolExample] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        input_data = item.get("input") or item.get("request") or {}
        output_data = item.get("output") or item.get("response") or item.get("expected") or {}
        if isinstance(input_data, dict) and isinstance(output_data, dict):
            examples.append(ToolExample(input=input_data, output=output_data))
    return examples


def _normalize_test_scenarios(value: Any) -> list[ToolTestScenario]:
    if not isinstance(value, list):
        return []
    scenarios: list[ToolTestScenario] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("title") or "scenario")
        input_data = item.get("input") or item.get("request") or {}
        expected_data = item.get("expected") or item.get("output") or item.get("response") or {}
        if isinstance(input_data, dict) and isinstance(expected_data, dict):
            scenarios.append(ToolTestScenario(name=name, input=input_data, expected=expected_data))
    return scenarios


def _normalize_sources(value: Any) -> list[ResearchSource]:
    if not isinstance(value, list):
        return []
    sources: list[ResearchSource] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or "source")
        url = str(item.get("url") or item.get("link") or "")
        summary = str(item.get("summary") or item.get("description") or item.get("content") or "")
        sources.append(ResearchSource(title=title, url=url, summary=summary))
    return sources


def _normalize_risk(value: Any) -> str:
    text = str(value or "low").strip().lower()
    if text in {"low", "medium", "high"}:
        return text
    return "low"

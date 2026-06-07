from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dynamic_mcp_skill_hub.codegen import generate_python_tool_code, generate_schema, generate_test_cases
from dynamic_mcp_skill_hub.models import Tool, ToolApproval, ToolSpec, ToolVersion
from dynamic_mcp_skill_hub.storage import FilesystemToolRegistry
from dynamic_mcp_skill_hub.workflow import ToolCreationWorkflow


class QueryInterceptor:
    def __init__(
        self,
        registry: FilesystemToolRegistry | None = None,
        workflow: ToolCreationWorkflow | None = None,
    ) -> None:
        self.registry = registry or FilesystemToolRegistry()
        self.workflow = workflow or ToolCreationWorkflow()

    def intercept(self, query: str) -> dict[str, Any]:
        self.registry.ensure_base_dirs()
        result = self.workflow.run(query)
        spec = result.get("tool_spec")
        if spec is None or not result.get("validation_passed"):
            return {
                "status": "rejected",
                "intent": result.get("intent"),
                "messages": result.get("messages", []),
            }

        version_number = self.registry.next_version_number(spec.name)
        tool_manifest = self._build_tool_manifest(spec, version_number)
        version_record = self._build_version_record(spec, version_number)
        schema = generate_schema(spec)
        code = generate_python_tool_code(spec)
        tests = generate_test_cases(spec)
        validation_report = {
            "passed": True,
            "checks": [{"name": "tool_spec_schema", "passed": True, "message": "Tool spec is valid."}],
        }
        publish_report = {
            "published": True,
            "notes": "Published from query interceptor.",
        }

        self.registry.save_tool_manifest(spec.name, tool_manifest)
        self.registry.persist_version_artifacts(
            tool_name=spec.name,
            version_number=version_number,
            spec=spec.model_dump(),
            schema=schema,
            code=code,
            tests=tests,
            validation_report=validation_report,
            publish_report=publish_report,
            version_record=version_record,
        )

        return {
            "status": "published",
            "tool_name": spec.name,
            "version": version_number,
            "intent": result.get("intent"),
            "messages": result.get("messages", []),
            "tool_path": str(self.registry.version_dir(spec.name, version_number)),
        }

    def _build_tool_manifest(self, spec: ToolSpec, version_number: str) -> Tool:
        existing_versions = self.registry.list_version_names(spec.name)
        now = self._now()
        return Tool(
            tool_id=spec.name,
            name=spec.name,
            versions=[*existing_versions, version_number],
            current_version=version_number,
            created_at=now,
            updated_at=now,
        )

    def _build_version_record(self, spec: ToolSpec, version_number: str) -> ToolVersion:
        now = self._now()
        return ToolVersion(
            tool_id=spec.name,
            version_number=version_number,
            status="published",
            created_at=now,
            updated_at=now,
            created_by="query_interceptor",
            spec_path=f"workspace/tools/{spec.name}/versions/{version_number}/spec.json",
            schema_path=f"workspace/tools/{spec.name}/versions/{version_number}/schema.json",
            code_path=f"workspace/tools/{spec.name}/versions/{version_number}/tool.py",
            approval=ToolApproval(
                required=False,
                approved=True,
                reason="Auto-published low-risk tool.",
            ),
            validation_report_path=f"workspace/tools/{spec.name}/versions/{version_number}/validation-report.json",
            publish_report_path=f"workspace/tools/{spec.name}/versions/{version_number}/publish-report.json",
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()


def write_query_result(result: dict[str, Any], output_path: Path | None = None) -> None:
    if output_path is None:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


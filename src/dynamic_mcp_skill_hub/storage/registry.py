import json
from pathlib import Path
from typing import Any

from dynamic_mcp_skill_hub.config import get_settings
from dynamic_mcp_skill_hub.models import Tool, ToolVersion


class FilesystemToolRegistry:
    def __init__(self, registry_dir: str | None = None) -> None:
        settings = get_settings()
        self.registry_dir = Path(registry_dir or settings.tool_registry_dir)
        self.runtime_dir = Path(settings.runtime_dir)
        self.log_dir = Path(settings.log_dir)

    def ensure_base_dirs(self) -> None:
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def tool_dir(self, tool_name: str) -> Path:
        return self.registry_dir / tool_name

    def version_dir(self, tool_name: str, version: str) -> Path:
        return self.tool_dir(tool_name) / "versions" / version

    def list_version_names(self, tool_name: str) -> list[str]:
        versions_root = self.tool_dir(tool_name) / "versions"
        if not versions_root.exists():
            return []
        return sorted(
            [
                path.name
                for path in versions_root.iterdir()
                if path.is_dir() and path.name.startswith("v")
            ],
            key=self._version_sort_key,
        )

    def next_version_number(self, tool_name: str) -> str:
        versions = self.list_version_names(tool_name)
        if not versions:
            return "v1"
        last = versions[-1]
        try:
            return f"v{int(last.removeprefix('v')) + 1}"
        except ValueError:
            return f"v{len(versions) + 1}"

    @staticmethod
    def _version_sort_key(version_name: str) -> tuple[int, str]:
        try:
            return (int(version_name.removeprefix("v")), version_name)
        except ValueError:
            return (0, version_name)

    def write_json(self, file_path: Path, data: Any) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def read_json(self, file_path: Path) -> Any:
        return json.loads(file_path.read_text(encoding="utf-8"))

    def save_text(self, file_path: Path, content: str) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def save_tool_manifest(self, tool_name: str, manifest: Tool) -> None:
        self.write_json(self.tool_dir(tool_name) / "manifests" / "tool.json", manifest.model_dump())

    def save_version_manifest(self, tool_name: str, version: ToolVersion) -> None:
        self.write_json(
            self.version_dir(tool_name, version.version_number) / "version.json",
            version.model_dump(),
        )

    def initialize_version_layout(self, tool_name: str, version_number: str) -> Path:
        version_dir = self.version_dir(tool_name, version_number)
        (version_dir / "tests").mkdir(parents=True, exist_ok=True)
        return version_dir

    def point_current_version(self, tool_name: str, version_number: str) -> None:
        self.write_json(
            self.tool_dir(tool_name) / "current.json",
            {"currentVersion": version_number},
        )

    def persist_version_artifacts(
        self,
        tool_name: str,
        version_number: str,
        spec: dict[str, Any],
        schema: dict[str, Any],
        code: str,
        tests: list[dict[str, Any]],
        validation_report: dict[str, Any],
        publish_report: dict[str, Any],
        version_record: ToolVersion,
    ) -> Path:
        version_dir = self.initialize_version_layout(tool_name, version_number)
        self.write_json(version_dir / "spec.json", spec)
        self.write_json(version_dir / "schema.json", schema)
        self.save_text(version_dir / "tool.py", code)
        self.write_json(version_dir / "tests" / f"{tool_name}.test.json", tests)
        self.write_json(version_dir / "validation-report.json", validation_report)
        self.write_json(version_dir / "publish-report.json", publish_report)
        self.save_version_manifest(tool_name, version_record)
        self.point_current_version(tool_name, version_number)
        return version_dir

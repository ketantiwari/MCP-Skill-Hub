from datetime import UTC, datetime
from uuid import uuid4

from dynamic_mcp_skill_hub.models import ToolRun


class SandboxRunner:
    def run(self, tool_id: str, version_number: str, input_data: dict[str, object]) -> ToolRun:
        started_at = datetime.now(UTC).isoformat()
        return ToolRun(
            run_id=str(uuid4()),
            tool_id=tool_id,
            version_number=version_number,
            input=input_data,
            output={
                "message": "Sandbox runner placeholder. Docker execution will be wired here."
            },
            started_at=started_at,
            finished_at=datetime.now(UTC).isoformat(),
        )


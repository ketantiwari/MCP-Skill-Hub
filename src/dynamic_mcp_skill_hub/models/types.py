from typing import Any, Literal

from pydantic import BaseModel, Field

ToolIntent = Literal["create_tool", "update_tool", "execute_tool", "version_tool", "rollback_tool"]
ToolStatus = Literal["draft", "validated", "published", "deprecated", "failed"]
RiskLevel = Literal["low", "medium", "high"]


class ToolDependency(BaseModel):
    name: str
    reason: str
    allowed: bool
    version: str | None = None


class ToolApproval(BaseModel):
    required: bool
    approved: bool
    reason: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None


class ToolExample(BaseModel):
    input: dict[str, Any]
    output: dict[str, Any]


class ToolTestScenario(BaseModel):
    name: str
    input: dict[str, Any]
    expected: dict[str, Any]


class ResearchSource(BaseModel):
    title: str
    url: str
    summary: str


class ToolSpec(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str
    tags: list[str]
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    side_effects: list[str]
    dependencies: list[ToolDependency]
    permissions: list[str]
    safety_constraints: list[str]
    risk_level: RiskLevel
    examples: list[ToolExample]
    test_scenarios: list[ToolTestScenario]
    research_sources: list[ResearchSource] = Field(default_factory=list)


class ToolVersion(BaseModel):
    tool_id: str
    version_number: str
    status: ToolStatus
    created_at: str
    updated_at: str
    created_by: str
    spec_path: str
    schema_path: str
    code_path: str
    approval: ToolApproval
    validation_report_path: str | None = None
    test_report_path: str | None = None
    publish_report_path: str | None = None


class Tool(BaseModel):
    tool_id: str
    name: str
    versions: list[str]
    created_at: str
    updated_at: str
    current_version: str | None = None


class ToolRun(BaseModel):
    run_id: str
    tool_id: str
    version_number: str
    input: dict[str, Any]
    started_at: str
    output: dict[str, Any] | None = None
    error: str | None = None
    finished_at: str | None = None


class ToolAuditLog(BaseModel):
    id: str
    action: str
    details: dict[str, Any]
    created_at: str
    tool_id: str | None = None
    version_number: str | None = None


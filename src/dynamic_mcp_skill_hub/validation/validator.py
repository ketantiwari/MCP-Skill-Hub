from dataclasses import dataclass

from pydantic import ValidationError

from dynamic_mcp_skill_hub.models import ToolSpec


@dataclass(frozen=True)
class ValidationCheck:
    name: str
    passed: bool
    message: str


@dataclass(frozen=True)
class ValidationReport:
    passed: bool
    checks: list[ValidationCheck]


class ToolValidator:
    def validate_spec(self, spec: object) -> ValidationReport:
        try:
            ToolSpec.model_validate(spec)
        except ValidationError as exc:
            return ValidationReport(
                passed=False,
                checks=[
                    ValidationCheck(
                        name="tool_spec_schema",
                        passed=False,
                        message=str(exc),
                    )
                ],
            )

        return ValidationReport(
            passed=True,
            checks=[
                ValidationCheck(
                    name="tool_spec_schema",
                    passed=True,
                    message="Tool spec is valid.",
                )
            ],
        )


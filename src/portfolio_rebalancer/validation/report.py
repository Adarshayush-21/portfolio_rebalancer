import json
from pathlib import Path
from dataclasses import asdict, dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: Literal["ERROR", "WARNING"]
    entity_type: str = ""
    entity_id: str = ""


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)
    checks_run: int = 0

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "ERROR"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "WARNING"]

    @property
    def passed(self) -> bool:
        return not self.errors

    def add(
        self,
        code: str,
        message: str,
        severity: Literal["ERROR", "WARNING"] = "ERROR",
        entity_type: str = "",
        entity_id: str = "",
    ) -> None:
        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                severity=severity,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks_run": self.checks_run,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [asdict(issue) for issue in self.issues],
        }


def write_validation_report(
    report: ValidationReport,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2),
        encoding="utf-8",
    )
    return path

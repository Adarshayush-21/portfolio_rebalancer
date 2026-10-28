
import json

from portfolio_rebalancer.validation.report import (
    ValidationReport,
    write_validation_report,
)


def test_report_passes_without_errors():
    report = ValidationReport()
    report.checks_run = 3
    report.add("STALE_PRICE", "Price is stale.", severity="WARNING")

    assert report.passed
    assert len(report.errors) == 0
    assert len(report.warnings) == 1


def test_report_fails_with_error():
    report = ValidationReport()
    report.add("INVALID_WEIGHT", "Weights do not sum to one.")

    assert not report.passed
    assert len(report.errors) == 1


def test_report_exports_json(tmp_path):
    report = ValidationReport()
    report.checks_run = 2
    report.add(
        "INVALID_WEIGHT",
        "Weights do not sum to one.",
        entity_type="portfolio",
        entity_id="PORT-INV-000001-01",
    )

    output = write_validation_report(
        report,
        tmp_path / "reports" / "validation.json",
    )

    data = json.loads(output.read_text(encoding="utf-8"))

    assert data["passed"] is False
    assert data["checks_run"] == 2
    assert data["error_count"] == 1
    assert data["issues"][0]["code"] == "INVALID_WEIGHT"


from collections.abc import Iterable, Mapping
from typing import Any


def evaluate_anomalies(
    ground_truth: Iterable[Mapping[str, Any]],
    validation_issues: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Match ground-truth anomalies to validation findings by code and entity."""

    issues = list(validation_issues)
    results = []

    for label in ground_truth:
        expected_code = label["expected_detection"]
        entity_type = label["entity_type"]
        entity_id = label["entity_id"]

        matches = [
            issue
            for issue in issues
            if issue.get("code") == expected_code
            and issue.get("entity_type") == entity_type
            and issue.get("entity_id") == entity_id
        ]

        results.append({
            "anomaly_id": label["anomaly_id"],
            "anomaly_type": label["anomaly_type"],
            "expected_detection": expected_code,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "detected": bool(matches),
            "matching_issue_count": len(matches),
        })

    detected_count = sum(result["detected"] for result in results)
    total_count = len(results)

    return {
        "total_count": total_count,
        "detected_count": detected_count,
        "missed_count": total_count - detected_count,
        "detection_rate": (
            detected_count / total_count if total_count else 1.0
        ),
        "results": results,
        "missed": [
            result for result in results if not result["detected"]
        ],
    }

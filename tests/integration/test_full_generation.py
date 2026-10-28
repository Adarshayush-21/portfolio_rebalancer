
import json

from portfolio_rebalancer.config import ProjectConfig
from portfolio_rebalancer.generator.pipeline import generate_dataset
from portfolio_rebalancer.evaluation.anomaly_metrics import evaluate_anomalies

def test_full_generation_pipeline(tmp_path):
    config = ProjectConfig(
        seed=20261022,
        portfolio_count=4,
        instrument_count=10,
        trading_days=10,
        start_date="2026-10-01",
        output_dir=tmp_path / "generated",
        ground_truth_dir=tmp_path / "ground_truth",
        database_path=tmp_path / "portfolio.db",
    )

    summary = generate_dataset(config)

    assert summary["master_data"]["investors"] == 4
    assert summary["master_data"]["portfolios"] == 4
    assert summary["master_data"]["instruments"] == 10
    assert summary["market_data"]["market_price_rows"] == 100
    assert summary["ground_truth_count"] == 6

    ground_truth = summary.get("ground_truth", [])
    if ground_truth:
        assert len(ground_truth) == 6

    generated = config.output_dir
    ground_truth_path = config.ground_truth_dir / "ground_truth.json"

    assert (generated / "investors.csv").exists() is False
    assert (generated / "investor_profiles.csv").exists()
    assert (generated / "market_prices.csv").exists()
    assert (generated / "seed.sql").exists()
    assert (generated / "baseline_validation.json").exists()
    assert (generated / "validation_report.json").exists()
    assert ground_truth_path.exists()

    labels = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    assert {label["anomaly_type"] for label in labels} == {
        "TARGET_WEIGHTS_NOT_100_PERCENT",
        "STALE_MARKET_PRICE",
        "MISSING_FEE_SCHEDULE",
        "TRADE_EXCEEDS_HOLDING",
        "EXCLUDED_INSTRUMENT_RECOMMENDED",
        "STALE_PRICE_USED_WITHOUT_WARNING",
}

    baseline = json.loads(
        (generated / "baseline_validation.json").read_text(encoding="utf-8")
    )
    assert baseline["passed"] is True

    final_report = json.loads(
        (generated / "validation_report.json").read_text(encoding="utf-8")
    )
    assert final_report["passed"] is False
    assert final_report["error_count"] >= 2
    assert final_report["warning_count"] >= 1

    stale_trade_label = next(
        label for label in labels
        if label["anomaly_id"] == "ANOM-000006"
    )
    assert stale_trade_label["entity_type"] == "trade"
    assert stale_trade_label["entity_id"] == "TR-ANOM-000006"
    assert stale_trade_label["expected_detection"] == "STALE_TRADE_PRICE"

    assert any(
        issue.get("code") == "STALE_TRADE_PRICE"
        and issue.get("entity_type") == "trade"
        and issue.get("entity_id") == "TR-ANOM-000006"
        for issue in final_report["issues"]
    )

    metrics = evaluate_anomalies(
        labels,
        final_report["issues"],
    )

    assert metrics["total_count"] == 6
    assert metrics["detected_count"] == 6, json.dumps(
        metrics["missed"],
        indent=2,
    )

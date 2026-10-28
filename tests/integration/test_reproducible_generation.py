
from portfolio_rebalancer.config import ProjectConfig
from portfolio_rebalancer.evaluation.reproducibility import (
    build_reproducibility_manifest,
    compare_reproducibility_manifests,
)
from portfolio_rebalancer.generator.pipeline import generate_dataset


def test_same_seed_generates_identical_outputs(tmp_path):
    output_dir = tmp_path / "generated"
    ground_truth_dir = output_dir / "ground_truth"

    config = ProjectConfig(
        seed=20261022,
        portfolio_count=4,
        instrument_count=10,
        trading_days=10,
        start_date="2026-10-01",
        output_dir=output_dir,
        ground_truth_dir=ground_truth_dir,
        database_path=tmp_path / "reproducibility.db",
    )

    first_summary = generate_dataset(config)
    first_manifest = build_reproducibility_manifest(
        output_dir,
        first_summary["csv_row_counts"],
    )

    second_summary = generate_dataset(config)
    second_manifest = build_reproducibility_manifest(
        output_dir,
        second_summary["csv_row_counts"],
    )

    comparison = compare_reproducibility_manifests(
        first_manifest,
        second_manifest,
    )

    assert first_summary["seed"] == second_summary["seed"]
    assert first_summary["csv_row_counts"] == second_summary["csv_row_counts"]
    assert comparison["reproducible"], (
        "Outputs changed between runs with the same seed:\n"
        f"{comparison}"
    )


import json

from portfolio_rebalancer.evaluation.reproducibility import (
    build_reproducibility_manifest,
    compare_reproducibility_manifests,
)


def test_same_files_produce_matching_manifests(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "instruments.csv").write_text(
        "instrument_id,symbol\nINS-000001,TEST\n",
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps({"seed": 20261022, "count": 1}, sort_keys=True),
        encoding="utf-8",
    )

    first = build_reproducibility_manifest(
        output_dir,
        {"instruments": 1},
    )
    second = build_reproducibility_manifest(
        output_dir,
        {"instruments": 1},
    )

    result = compare_reproducibility_manifests(first, second)

    assert result["reproducible"] is True
    assert result["row_counts_match"] is True


def test_changed_file_is_reported(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    target = output_dir / "instruments.csv"
    target.write_text("instrument_id\nINS-000001\n", encoding="utf-8")

    first = build_reproducibility_manifest(output_dir)

    target.write_text("instrument_id\nINS-000002\n", encoding="utf-8")
    second = build_reproducibility_manifest(output_dir)

    result = compare_reproducibility_manifests(first, second)

    assert result["reproducible"] is False
    assert result["changed_files"] == ["instruments.csv"]


def test_added_and_missing_files_are_reported(tmp_path):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()

    (first_dir / "old.csv").write_text("old\n", encoding="utf-8")
    (second_dir / "new.csv").write_text("new\n", encoding="utf-8")

    first = build_reproducibility_manifest(first_dir)
    second = build_reproducibility_manifest(second_dir)

    result = compare_reproducibility_manifests(first, second)

    assert result["reproducible"] is False
    assert result["added_files"] == ["new.csv"]
    assert result["missing_files"] == ["old.csv"]

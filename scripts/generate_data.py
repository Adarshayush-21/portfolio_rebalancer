
import argparse
import json
from pathlib import Path

from portfolio_rebalancer.config import DEFAULT_CONFIG, ProjectConfig
from portfolio_rebalancer.generator.pipeline import generate_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a reproducible portfolio rebalancing dataset."
    )
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--ground-truth-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    parser.add_argument(
        "--portfolios", type=int, default=DEFAULT_CONFIG.portfolio_count
    )
    parser.add_argument(
        "--instruments", type=int, default=DEFAULT_CONFIG.instrument_count
    )
    parser.add_argument(
        "--trading-days", type=int, default=DEFAULT_CONFIG.trading_days
    )
    parser.add_argument(
        "--start-date", default=DEFAULT_CONFIG.start_date
    )
    parser.add_argument(
        "--no-anomalies",
        action="store_true",
        help="Generate clean baseline data without injected anomalies.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    config = ProjectConfig(
        seed=args.seed,
        portfolio_count=args.portfolios,
        instrument_count=args.instruments,
        trading_days=args.trading_days,
        start_date=args.start_date,
        output_dir=args.output_dir,
        ground_truth_dir=args.ground_truth_dir,
        database_path=args.database,
    )

    summary = generate_dataset(
        config=config,
        reset_database=True,
        include_anomalies=not args.no_anomalies,
    )
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

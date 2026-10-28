
import argparse
import json
from datetime import date
from decimal import Decimal

from portfolio_rebalancer.config import DEFAULT_CONFIG
from portfolio_rebalancer.database.connection import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from portfolio_rebalancer.rebalancer.workflow import run_rebalancing


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a policy-constrained rebalance proposal."
    )
    parser.add_argument(
        "--portfolio-id",
        required=True,
        help="Portfolio identifier, for example PORT-INV-000001-01",
    )
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        help="Valuation date in YYYY-MM-DD format; defaults to latest holdings date",
    )
    parser.add_argument(
        "--proposal-id",
        help="Optional proposal ID in RB-YYYY-NNNNNN format",
    )
    parser.add_argument(
        "--drift-tolerance",
        type=Decimal,
        default=Decimal("0.01"),
        help="Allocation drift tolerance as a fraction; default 0.01",
    )
    parser.add_argument(
        "--database",
        help="SQLite database path; defaults to the project configuration",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.drift_tolerance < Decimal("0"):
        parser.error("--drift-tolerance cannot be negative")

    engine = create_database_engine(
        args.database or DEFAULT_CONFIG.database_path
    )
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            with session.begin():
                result = run_rebalancing(
                    session=session,
                    portfolio_id=args.portfolio_id,
                    as_of_date=args.as_of_date,
                    proposal_id=args.proposal_id,
                    drift_tolerance=args.drift_tolerance,
                )

        print(json.dumps(result, indent=2))
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())


import argparse
import json
from datetime import date
from pathlib import Path

from portfolio_rebalancer.config import DEFAULT_CONFIG
from portfolio_rebalancer.database.connection import (
    create_database_engine,
    create_session_factory,
)
from portfolio_rebalancer.generator.market_data import trading_dates
from portfolio_rebalancer.validation.business_rules import validate_business_rules
from portfolio_rebalancer.validation.integrity import validate_database_integrity
from portfolio_rebalancer.validation.report import (
    ValidationReport,
    write_validation_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate database integrity and portfolio business rules."
    )
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--as-of-date", type=date.fromisoformat)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/validation_report.json"),
    )
    args = parser.parse_args()

    if not args.database.is_file():
        parser.error(f"Database does not exist: {args.database}")

    as_of_date = args.as_of_date or trading_dates(
        DEFAULT_CONFIG.start_date,
        DEFAULT_CONFIG.trading_days,
    )[-1]

    engine = create_database_engine(args.database)
    try:
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            integrity = validate_database_integrity(session)
            business = validate_business_rules(session, as_of_date)

            report = ValidationReport(
                issues=integrity.issues + business.issues,
                checks_run=integrity.checks_run + business.checks_run,
            )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_validation_report(report, args.output)

        print(
            json.dumps(
                {
                    "database": str(args.database),
                    "as_of_date": as_of_date.isoformat(),
                    "passed": report.passed,
                    "errors": len(report.errors),
                    "warnings": len(report.warnings),
                    "report": str(args.output),
                },
                indent=2,
            )
        )
        return 0 if report.passed else 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

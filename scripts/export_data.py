
import argparse
import json
from pathlib import Path

from portfolio_rebalancer.database.connection import create_database_engine
from portfolio_rebalancer.reporting.csv_export import export_tables_to_csv
from portfolio_rebalancer.reporting.sql_export import export_sqlite_dump


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export database tables to CSV and SQL."
    )
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    if not args.database.is_file():
        parser.error(f"Database does not exist: {args.database}")

    engine = create_database_engine(args.database)
    try:
        csv_counts = export_tables_to_csv(engine, args.output_dir)
        sql_path = export_sqlite_dump(
            args.database, args.output_dir / "seed.sql"
        )
    finally:
        engine.dispose()

    print(
        json.dumps(
            {
                "csv_row_counts": csv_counts,
                "sql_export": str(sql_path),
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

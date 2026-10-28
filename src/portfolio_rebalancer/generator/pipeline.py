
from pathlib import Path

from portfolio_rebalancer.config import DEFAULT_CONFIG, ProjectConfig
from portfolio_rebalancer.database.connection import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from portfolio_rebalancer.database.schema import Base
from portfolio_rebalancer.generator.anomaly_injection import inject_anomalies
from portfolio_rebalancer.generator.holdings import generate_holdings_and_targets
from portfolio_rebalancer.generator.master_data import generate_master_data
from portfolio_rebalancer.generator.market_data import (
    generate_market_data,
    trading_dates,
)
from portfolio_rebalancer.generator.policies import generate_policies
from portfolio_rebalancer.reporting.csv_export import export_tables_to_csv
from portfolio_rebalancer.reporting.json_export import write_json
from portfolio_rebalancer.reporting.sql_export import export_sqlite_dump
from portfolio_rebalancer.validation.business_rules import validate_business_rules
from portfolio_rebalancer.validation.integrity import validate_database_integrity
from portfolio_rebalancer.validation.report import (
    ValidationReport,
    write_validation_report,
)


def generate_dataset(
    config: ProjectConfig = DEFAULT_CONFIG,
    reset_database: bool = True,
    include_anomalies: bool = True,
) -> dict:
    config.validate()

    output_dir = Path(config.output_dir)
    ground_truth_dir = Path(config.ground_truth_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    engine = create_database_engine(config.database_path)

    try:
        if reset_database:
            Base.metadata.drop_all(engine)

        initialize_database(engine)
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            master_counts = generate_master_data(session, config)
            session.commit()

            market_counts = generate_market_data(session, config)
            session.commit()

            holding_counts = generate_holdings_and_targets(session, config)
            session.commit()

            policy_counts = generate_policies(session, config)
            session.commit()

            as_of_date = trading_dates(
                config.start_date,
                config.trading_days,
            )[-1]

            baseline_integrity = validate_database_integrity(session)
            baseline_business = validate_business_rules(session, as_of_date)

            baseline_report = ValidationReport(
                issues=baseline_integrity.issues + baseline_business.issues,
                checks_run=(
                    baseline_integrity.checks_run
                    + baseline_business.checks_run
                ),
            )
            write_validation_report(
                baseline_report,
                output_dir / "baseline_validation.json",
            )

            ground_truth = (
                inject_anomalies(session, config)
                if include_anomalies
                else []
            )
            session.commit()

            final_integrity = validate_database_integrity(session)
            final_business = validate_business_rules(session, as_of_date)

            final_report = ValidationReport(
                issues=final_integrity.issues + final_business.issues,
                checks_run=(
                    final_integrity.checks_run
                    + final_business.checks_run
                ),
            )
            write_validation_report(
                final_report,
                output_dir / "validation_report.json",
            )

        csv_counts = export_tables_to_csv(engine, output_dir)
        sql_path = export_sqlite_dump(
            config.database_path,
            output_dir / "seed.sql",
        )

        write_json(
            ground_truth,
            ground_truth_dir / "ground_truth.json",
        )

        summary = {
            "seed": config.seed,
            "portfolio_count": config.portfolio_count,
            "instrument_count": config.instrument_count,
            "trading_days": config.trading_days,
            "as_of_date": as_of_date.isoformat(),
            "master_data": master_counts,
            "market_data": market_counts,
            "holdings_and_targets": holding_counts,
            "policies": policy_counts,
            "csv_row_counts": csv_counts,
            "ground_truth_count": len(ground_truth),
            "validation_passed": final_report.passed,
            "validation_errors": len(final_report.errors),
            "validation_warnings": len(final_report.warnings),
            "sql_export": str(sql_path),
        }

        write_json(summary, output_dir / "generation_summary.json")
        return summary
    finally:
        engine.dispose()

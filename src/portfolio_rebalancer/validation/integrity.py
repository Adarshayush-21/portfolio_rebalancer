
from sqlalchemy import text
from sqlalchemy.orm import Session

from portfolio_rebalancer.validation.report import ValidationReport


def validate_database_integrity(session: Session) -> ValidationReport:
    report = ValidationReport()

    integrity_results = session.execute(text("PRAGMA integrity_check")).scalars().all()
    report.checks_run += 1

    if integrity_results != ["ok"]:
        report.add(
            code="DATABASE_INTEGRITY_FAILURE",
            message="; ".join(integrity_results),
        )

    foreign_key_results = session.execute(
        text("PRAGMA foreign_key_check")
    ).all()
    report.checks_run += 1

    for result in foreign_key_results:
        table, row_id, parent, foreign_key_index = result
        report.add(
            code="FOREIGN_KEY_VIOLATION",
            message=(
                f"Table {table}, row {row_id}, references missing parent "
                f"in {parent}; foreign key index {foreign_key_index}"
            ),
            entity_type=table,
            entity_id=str(row_id),
        )

    return report

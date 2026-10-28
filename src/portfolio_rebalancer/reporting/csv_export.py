
import csv
from pathlib import Path

from sqlalchemy import Engine, select

from portfolio_rebalancer.database.schema import Base


def export_tables_to_csv(
    engine: Engine,
    output_dir: str | Path,
) -> dict[str, int]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    row_counts: dict[str, int] = {}

    with engine.connect() as connection:
        for table in Base.metadata.sorted_tables:
            result = connection.execute(select(table))
            path = destination / f"{table.name}.csv"
            count = 0

            with path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(result.keys())

                for row in result:
                    writer.writerow([
                        value.isoformat()
                        if hasattr(value, "isoformat")
                        else str(value) if value is not None else ""
                        for value in row
                    ])
                    count += 1

            row_counts[table.name] = count

    return row_counts

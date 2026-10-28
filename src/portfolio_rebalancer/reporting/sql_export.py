
import sqlite3
from pathlib import Path


def export_sqlite_dump(
    database_path: str | Path,
    output_path: str | Path,
) -> Path:
    source = Path(database_path)
    destination = Path(output_path)

    if not source.exists():
        raise FileNotFoundError(f"Database not found: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(source) as connection:
        with destination.open("w", encoding="utf-8", newline="\n") as file:
            for statement in connection.iterdump():
                file.write(statement)
                file.write("\n")

    return destination

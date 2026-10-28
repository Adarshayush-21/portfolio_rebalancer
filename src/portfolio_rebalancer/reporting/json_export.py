
import json
from pathlib import Path
from typing import Any


def write_json(data: Any, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )
    return path

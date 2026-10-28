
import hashlib
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 hash of a file's bytes."""
    digest = hashlib.sha256()

    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def build_reproducibility_manifest(
    output_dir: str | Path,
    row_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Record file hashes and optional row counts for generated outputs."""
    directory = Path(output_dir)

    if not directory.is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {directory}")

    files = {}

    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "reproducibility_manifest.json":
            relative_path = path.relative_to(directory).as_posix()
            files[relative_path] = {
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }

    return {
        "files": files,
        "row_counts": dict(sorted((row_counts or {}).items())),
    }


def compare_reproducibility_manifests(
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, Any]:
    """Compare two manifests and report changed, added, or missing files."""
    first_files = first.get("files", {})
    second_files = second.get("files", {})

    first_names = set(first_files)
    second_names = set(second_files)

    added = sorted(second_names - first_names)
    missing = sorted(first_names - second_names)

    changed = sorted(
        name
        for name in first_names & second_names
        if first_files[name] != second_files[name]
    )

    row_counts_match = first.get("row_counts", {}) == second.get(
        "row_counts", {}
    )

    return {
        "reproducible": not added and not missing and not changed and row_counts_match,
        "added_files": added,
        "missing_files": missing,
        "changed_files": changed,
        "row_counts_match": row_counts_match,
    }

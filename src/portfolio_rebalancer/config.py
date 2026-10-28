
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectConfig:
    """Central configuration for reproducible simulation runs."""

    seed: int = 20261022
    portfolio_count: int = 1_000
    instrument_count: int = 5_000
    trading_days: int = 250
    start_date: str = "2025-10-01"
    output_dir: Path = Path("data/generated")
    ground_truth_dir: Path = Path("data/ground_truth")
    database_path: Path = Path("data/portfolio_rebalancer.db")

    def validate(self) -> None:
        if self.portfolio_count < 1:
            raise ValueError("portfolio_count must be at least 1")
        if self.instrument_count < 1:
            raise ValueError("instrument_count must be at least 1")
        if self.trading_days < 1:
            raise ValueError("trading_days must be at least 1")
        if not 0 <= self.seed <= 2**32 - 1:
            raise ValueError("seed must be between 0 and 2**32 - 1")


DEFAULT_CONFIG = ProjectConfig()

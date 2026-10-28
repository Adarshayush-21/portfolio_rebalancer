
import random
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from portfolio_rebalancer.config import DEFAULT_CONFIG, ProjectConfig
from portfolio_rebalancer.generator.ids import (
    instrument_id,
    investor_id,
    portfolio_id,
)
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.investor import InvestorProfile
from portfolio_rebalancer.models.portfolio import Portfolio


ASSET_CLASSES = ("EQUITY", "BOND", "GOLD", "CASH", "OTHER")
RISK_PROFILES = ("CONSERVATIVE", "MODERATE", "AGGRESSIVE")


def generate_master_data(
    session: Session,
    config: ProjectConfig = DEFAULT_CONFIG,
) -> dict[str, int]:
    config.validate()
    rng = random.Random(config.seed)

    generated_at = datetime.fromisoformat(config.start_date).replace(
        tzinfo=timezone.utc
    )

    investors = [
        InvestorProfile(
            investor_id=investor_id(number),
            risk_profile=rng.choice(RISK_PROFILES),
            status="ACTIVE",
            created_at=generated_at,
        )
        for number in range(1, config.portfolio_count + 1)
    ]

    portfolios = [
        Portfolio(
            portfolio_id=portfolio_id(number),
            investor_id=investor_id(number),
            currency="INR",
            status="ACTIVE",
        )
        for number in range(1, config.portfolio_count + 1)
    ]

    instruments = [
        Instrument(
            instrument_id=instrument_id(number),
            symbol=f"SYN{number:05d}",
            name=f"Synthetic Instrument {number:05d}",
            asset_class=rng.choices(
                ASSET_CLASSES,
                weights=(50, 20, 10, 10, 10),
                k=1,
            )[0],
            currency="INR",
            status="ACTIVE",
        )
        for number in range(1, config.instrument_count + 1)
    ]

    session.add_all(investors)
    session.add_all(portfolios)
    session.add_all(instruments)
    session.flush()

    return {
        "investors": len(investors),
        "portfolios": len(portfolios),
        "instruments": len(instruments),
    }

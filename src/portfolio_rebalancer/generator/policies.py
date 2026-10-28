
import random
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_rebalancer.config import DEFAULT_CONFIG, ProjectConfig
from portfolio_rebalancer.models.constraint import Constraint
from portfolio_rebalancer.models.fee_schedule import FeeSchedule
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.portfolio import Portfolio


def generate_policies(
    session: Session,
    config: ProjectConfig = DEFAULT_CONFIG,
) -> dict[str, int]:
    config.validate()
    rng = random.Random(config.seed + 3)
    effective_from = date.fromisoformat(config.start_date)

    instruments = session.scalars(
        select(Instrument).order_by(Instrument.instrument_id)
    ).all()
    portfolios = session.scalars(
        select(Portfolio).order_by(Portfolio.portfolio_id)
    ).all()

    fee_schedules = [
        FeeSchedule(
            fee_schedule_id=f"FEE-{instrument.instrument_id}-01",
            instrument_id=instrument.instrument_id,
            asset_class=None,
            fee_rate=Decimal("0.001"),
            fixed_fee=Decimal("5.00"),
            minimum_fee=Decimal("5.00"),
            effective_from=effective_from,
        )
        for instrument in instruments
    ]

    constraints: list[Constraint] = []

    for portfolio in portfolios:
        constraints.append(
            Constraint(
                constraint_id=f"CNS-{portfolio.portfolio_id}-MAXTRADE",
                portfolio_id=portfolio.portfolio_id,
                constraint_type="MAX_TRADE_VALUE",
                parameters={"max_value": "100000.00"},
                effective_from=effective_from,
                status="ACTIVE",
            )
        )

        if rng.random() < 0.05 and instruments:
            instrument = rng.choice(instruments)
            constraints.append(
                Constraint(
                    constraint_id=f"CNS-{portfolio.portfolio_id}-EXCLUDE",
                    portfolio_id=portfolio.portfolio_id,
                    instrument_id=instrument.instrument_id,
                    constraint_type="EXCLUDE_INSTRUMENT",
                    parameters={},
                    effective_from=effective_from,
                    status="ACTIVE",
                )
            )

    session.add_all(fee_schedules)
    session.add_all(constraints)
    session.flush()

    return {
        "fee_schedules": len(fee_schedules),
        "constraints": len(constraints),
    }

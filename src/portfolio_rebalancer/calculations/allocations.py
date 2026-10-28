
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_rebalancer.calculations.valuation import ValuedHolding, total_market_value
from portfolio_rebalancer.models.target_allocation import TargetAllocation


def calculate_actual_allocations(
    valued_holdings: list[ValuedHolding],
) -> dict[str, Decimal]:
    total_value = total_market_value(valued_holdings)

    if total_value <= 0:
        raise ValueError("Portfolio market value must be positive")

    values_by_class: dict[str, Decimal] = {}

    for holding in valued_holdings:
        values_by_class[holding.asset_class] = (
            values_by_class.get(holding.asset_class, Decimal("0"))
            + holding.market_value
        )

    return {
        asset_class: value / total_value
        for asset_class, value in values_by_class.items()
    }


def get_active_target_allocations(
    session: Session,
    portfolio_id: str,
    as_of_date: date,
) -> dict[str, Decimal]:
    targets = session.scalars(
        select(TargetAllocation).where(
            TargetAllocation.portfolio_id == portfolio_id,
            TargetAllocation.effective_from <= as_of_date,
        ).order_by(
            TargetAllocation.asset_class,
            TargetAllocation.effective_from.desc(),
        )
    ).all()

    active_by_class: dict[str, TargetAllocation] = {}

    for target in targets:
        if target.effective_to is not None and target.effective_to < as_of_date:
            continue

        if target.asset_class in active_by_class:
            current = active_by_class[target.asset_class]

            if current.effective_from == target.effective_from:
                raise ValueError(
                    f"Overlapping target allocations for asset class "
                    f"{target.asset_class}"
                )

            continue

        active_by_class[target.asset_class] = target

    if not active_by_class:
        raise ValueError(
            f"No active target allocations for portfolio {portfolio_id}"
        )

    total_weight = sum(
        (target.target_weight for target in active_by_class.values()),
        Decimal("0"),
    )

    if abs(total_weight - Decimal("1")) > Decimal("0.0001"):
        raise ValueError(
            f"Target allocation weights total {total_weight}, expected 1.0"
        )

    return {
        asset_class: target.target_weight
        for asset_class, target in active_by_class.items()
    }


from datetime import date
from decimal import Decimal

from portfolio_rebalancer.models.constraint import Constraint


ZERO = Decimal("0")


def evaluate_trade_constraints(
    portfolio_id: str,
    instrument_id: str,
    instrument_status: str,
    side: str,
    notional: Decimal,
    as_of_date: date,
    constraints: list[Constraint],
) -> list[str]:
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")

    if notional < ZERO:
        raise ValueError("notional cannot be negative")

    reasons: list[str] = []

    if side == "BUY" and instrument_status == "EXCLUDED":
        reasons.append("BUY_EXCLUDED_INSTRUMENT")

    for constraint in constraints:
        if constraint.status != "ACTIVE":
            continue

        if constraint.effective_from > as_of_date:
            continue

        if constraint.effective_to is not None and constraint.effective_to < as_of_date:
            continue

        if (
            constraint.portfolio_id is not None
            and constraint.portfolio_id != portfolio_id
        ):
            continue

        if (
            constraint.instrument_id is not None
            and constraint.instrument_id != instrument_id
        ):
            continue

        constraint_type = constraint.constraint_type
        parameters = constraint.parameters or {}

        if constraint_type == "EXCLUDE_INSTRUMENT" and side == "BUY":
            reasons.append("BUY_CONSTRAINED_INSTRUMENT")

        elif constraint_type == "BLOCK_BUY" and side == "BUY":
            reasons.append("BUY_BLOCKED")

        elif constraint_type == "BLOCK_SELL" and side == "SELL":
            reasons.append("SELL_BLOCKED")

        elif constraint_type == "MAX_TRADE_VALUE":
            maximum = Decimal(str(parameters.get("max_value", "0")))
            if notional > maximum:
                reasons.append("MAX_TRADE_VALUE_EXCEEDED")

        elif constraint_type == "MIN_TRADE_VALUE":
            minimum = Decimal(str(parameters.get("min_value", "0")))
            if notional < minimum:
                reasons.append("MIN_TRADE_VALUE_VIOLATED")

    return sorted(set(reasons))

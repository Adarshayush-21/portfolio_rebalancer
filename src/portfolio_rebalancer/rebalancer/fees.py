
from datetime import date
from decimal import Decimal

from portfolio_rebalancer.models.fee_schedule import FeeSchedule


ZERO = Decimal("0")


def select_fee_schedule(
    schedules: list[FeeSchedule],
    instrument_id: str,
    asset_class: str,
    as_of_date: date,
) -> FeeSchedule:
    applicable = [
        schedule
        for schedule in schedules
        if schedule.effective_from <= as_of_date
        and (
            schedule.effective_to is None
            or schedule.effective_to >= as_of_date
        )
        and (
            schedule.instrument_id == instrument_id
            or schedule.asset_class == asset_class
            or (
                schedule.instrument_id is None
                and schedule.asset_class is None
            )
        )
    ]

    applicable.sort(
        key=lambda schedule: (
            schedule.instrument_id == instrument_id,
            schedule.asset_class == asset_class,
        ),
        reverse=True,
    )

    if not applicable:
        raise ValueError(
            f"No fee schedule for instrument {instrument_id} on {as_of_date}"
        )

    return applicable[0]


def calculate_trade_fee(
    notional: Decimal,
    schedule: FeeSchedule,
) -> Decimal:
    if notional < ZERO:
        raise ValueError("notional cannot be negative")

    if schedule.fee_rate < ZERO:
        raise ValueError("fee_rate cannot be negative")

    if schedule.fixed_fee < ZERO or schedule.minimum_fee < ZERO:
        raise ValueError("fixed and minimum fees cannot be negative")

    fee = max(
        notional * schedule.fee_rate + schedule.fixed_fee,
        schedule.minimum_fee,
    )
    return fee.quantize(Decimal("0.01"))

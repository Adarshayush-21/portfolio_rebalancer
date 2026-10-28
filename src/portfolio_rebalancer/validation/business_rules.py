
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_rebalancer.models.constraint import Constraint
from portfolio_rebalancer.models.fee_schedule import FeeSchedule
from portfolio_rebalancer.models.holding import Holding
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.market_price import MarketPrice
from portfolio_rebalancer.models.portfolio import Portfolio
from portfolio_rebalancer.models.rebalance_proposal import RebalanceProposal
from portfolio_rebalancer.models.target_allocation import TargetAllocation
from portfolio_rebalancer.models.trade import Trade
from portfolio_rebalancer.validation.report import ValidationReport


ZERO = Decimal("0")
ONE = Decimal("1")
TOLERANCE = Decimal("0.0001")
FEE_TOLERANCE = Decimal("0.01")


def validate_business_rules(
    session: Session,
    as_of_date: date,
    stale_after_days: int = 3,
) -> ValidationReport:
    if stale_after_days < 0:
        raise ValueError("stale_after_days cannot be negative")

    report = ValidationReport()

    portfolios = session.scalars(select(Portfolio)).all()
    instruments = {
        instrument.instrument_id: instrument
        for instrument in session.scalars(select(Instrument)).all()
    }
    holdings = session.scalars(select(Holding)).all()
    targets = session.scalars(select(TargetAllocation)).all()
    prices = session.scalars(select(MarketPrice)).all()
    constraints = session.scalars(select(Constraint)).all()
    proposals = session.scalars(select(RebalanceProposal)).all()
    trades = session.scalars(select(Trade)).all()
    fee_schedules = session.scalars(select(FeeSchedule)).all()

    active_portfolios = {
        portfolio.portfolio_id: portfolio
        for portfolio in portfolios
        if portfolio.status == "ACTIVE"
    }

    report.checks_run += 1

    for holding in holdings:
        if holding.quantity < ZERO:
            report.add(
                "NEGATIVE_HOLDING",
                "Holding quantity cannot be negative.",
                entity_type="holding",
                entity_id=holding.holding_id,
            )

        if holding.as_of_date > as_of_date:
            report.add(
                "FUTURE_HOLDING",
                "Holding date is after the validation date.",
                entity_type="holding",
                entity_id=holding.holding_id,
            )

    report.checks_run += 1

    active_targets_by_portfolio: dict[str, list[TargetAllocation]] = {}

    for target in targets:
        if target.effective_from > as_of_date:
            continue

        if target.effective_to is not None and target.effective_to < as_of_date:
            continue

        active_targets_by_portfolio.setdefault(
            target.portfolio_id, []
        ).append(target)

    for portfolio_id in active_portfolios:
        active_targets = active_targets_by_portfolio.get(portfolio_id, [])

        if not active_targets:
            report.add(
                "MISSING_TARGET_ALLOCATION",
                "Active portfolio has no target allocation effective on the validation date.",
                entity_type="portfolio",
                entity_id=portfolio_id,
            )
            continue

        latest_by_class: dict[str, TargetAllocation] = {}

        for target in active_targets:
            current = latest_by_class.get(target.asset_class)

            if current is None or target.effective_from > current.effective_from:
                latest_by_class[target.asset_class] = target

        if len(latest_by_class) != len(active_targets):
            report.add(
                "OVERLAPPING_TARGET_ALLOCATION",
                "Multiple effective target rows exist for the same asset class.",
                entity_type="portfolio",
                entity_id=portfolio_id,
            )

        total_weight = sum(
            (target.target_weight for target in latest_by_class.values()),
            ZERO,
        )

        if abs(total_weight - ONE) > TOLERANCE:
            report.add(
                "TARGET_WEIGHTS_NOT_100_PERCENT",
                f"Active target weights total {total_weight}, expected 1.0.",
                entity_type="portfolio",
                entity_id=portfolio_id,
            )

    latest_prices: dict[str, MarketPrice] = {}

    for price in prices:
        if price.price_date > as_of_date:
            continue

        current = latest_prices.get(price.instrument_id)

        if current is None or price.price_date > current.price_date:
            latest_prices[price.instrument_id] = price

    report.checks_run += 1
    stale_cutoff = as_of_date - timedelta(days=stale_after_days)

    for holding in holdings:
        if holding.as_of_date != as_of_date:
            continue

        price = latest_prices.get(holding.instrument_id)

        if (
            price is None
            or price.price is None
            or price.price <= ZERO
            or price.quality in {"MISSING", "INVALID"}
        ):
            report.add(
                "UNUSABLE_MARKET_PRICE",
                "Holding has no usable market price on or before the validation date.",
                entity_type="holding",
                entity_id=holding.holding_id,
            )
        elif price.quality == "STALE" or price.price_date < stale_cutoff:
            report.add(
                "STALE_MARKET_PRICE",
                f"Latest price date is {price.price_date}; validation date is {as_of_date}.",
                severity="WARNING",
                entity_type="holding",
                entity_id=holding.holding_id,
            )

    holdings_by_portfolio_instrument: dict[tuple[str, str], Decimal] = {}

    for holding in holdings:
        if holding.as_of_date != as_of_date:
            continue

        key = (holding.portfolio_id, holding.instrument_id)
        holdings_by_portfolio_instrument[key] = (
            holdings_by_portfolio_instrument.get(key, ZERO) + holding.quantity
        )

    active_constraints_by_portfolio: dict[str, list[Constraint]] = {}
    active_global_constraints: list[Constraint] = []

    for constraint in constraints:
        if constraint.status != "ACTIVE":
            continue

        if constraint.effective_from > as_of_date:
            continue

        if constraint.effective_to is not None and constraint.effective_to < as_of_date:
            continue

        if constraint.portfolio_id is None:
            active_global_constraints.append(constraint)
        else:
            active_constraints_by_portfolio.setdefault(
                constraint.portfolio_id, []
            ).append(constraint)

    report.checks_run += 1

    for instrument in instruments.values():
        if instrument.status != "ACTIVE":
            continue

        applicable_schedules = [
            schedule
            for schedule in fee_schedules
            if schedule.effective_from <= as_of_date
            and (
                schedule.effective_to is None
                or schedule.effective_to >= as_of_date
            )
            and (
                schedule.instrument_id == instrument.instrument_id
                or schedule.asset_class == instrument.asset_class
                or (
                    schedule.instrument_id is None
                    and schedule.asset_class is None
                )
            )
        ]

        if not applicable_schedules:
            report.add(
                "MISSING_FEE_SCHEDULE",
                "No applicable fee schedule exists for the active instrument.",
                entity_type="instrument",
                entity_id=instrument.instrument_id,
            )

    proposal_map = {proposal.proposal_id: proposal for proposal in proposals}

    report.checks_run += 1

    for trade in trades:
        proposal = proposal_map.get(trade.proposal_id)

        if proposal is None:
            report.add(
                "TRADE_WITHOUT_PROPOSAL",
                "Trade references a missing proposal.",
                entity_type="trade",
                entity_id=trade.trade_id,
            )
            continue

        instrument = instruments.get(trade.instrument_id)

        if instrument is None:
            report.add(
                "TRADE_WITHOUT_INSTRUMENT",
                "Trade references a missing instrument.",
                entity_type="trade",
                entity_id=trade.trade_id,
            )
            continue

        if proposal.as_of_date != as_of_date:
            continue

        if trade.status not in {"PROPOSED", "APPROVED", "EXECUTED"}:
            continue

        latest_market_price = max(
            (
                price
                for price in prices
                if price.instrument_id == trade.instrument_id
                and price.price_date <= proposal.as_of_date
                and price.price is not None
                and price.price > ZERO
                and price.quality == "VALID"
            ),
            key=lambda price: price.price_date,
            default=None,
        )

        if (
            latest_market_price is not None
            and latest_market_price.price_date >= stale_cutoff
            and latest_market_price.price != trade.price
            and any(
                price.instrument_id == trade.instrument_id
                and price.price_date < stale_cutoff
                and price.price_date < latest_market_price.price_date
                and price.price is not None
                and price.price > ZERO
                and price.quality == "VALID"
                and price.price == trade.price
                for price in prices
            )
        ):
            report.add(
                "STALE_TRADE_PRICE",
                "Trade uses a historical market price despite a newer valid price.",
                severity="WARNING",
                entity_type="trade",
                entity_id=trade.trade_id,
            )

        if instrument.status == "EXCLUDED" and trade.side == "BUY":
            report.add(
                "BUY_EXCLUDED_INSTRUMENT",
                "Buy trade recommends an excluded instrument.",
                entity_type="trade",
                entity_id=trade.trade_id,
            )

        held_quantity = holdings_by_portfolio_instrument.get(
            (proposal.portfolio_id, trade.instrument_id),
            ZERO,
        )

        if trade.side == "SELL" and trade.quantity > held_quantity:
            report.add(
                "TRADE_EXCEEDS_HOLDING",
                f"Sell quantity {trade.quantity} exceeds holding {held_quantity}.",
                entity_type="trade",
                entity_id=trade.trade_id,
            )

        applicable_constraints = (
            active_constraints_by_portfolio.get(proposal.portfolio_id, [])
            + active_global_constraints
        )

        for constraint in applicable_constraints:
            if (
                constraint.instrument_id is not None
                and constraint.instrument_id != trade.instrument_id
            ):
                continue

            if (
                constraint.constraint_type == "EXCLUDE_INSTRUMENT"
                and trade.side == "BUY"
            ):
                report.add(
                    "BUY_CONSTRAINED_INSTRUMENT",
                    "Buy trade violates an active instrument exclusion constraint.",
                    entity_type="trade",
                    entity_id=trade.trade_id,
                )

            if (
                constraint.constraint_type == "BLOCK_BUY"
                and trade.side == "BUY"
            ):
                report.add(
                    "BUY_BLOCKED",
                    "Buy trade violates an active block-buy constraint.",
                    entity_type="trade",
                    entity_id=trade.trade_id,
                )

            if (
                constraint.constraint_type == "BLOCK_SELL"
                and trade.side == "SELL"
            ):
                report.add(
                    "SELL_BLOCKED",
                    "Sell trade violates an active block-sell constraint.",
                    entity_type="trade",
                    entity_id=trade.trade_id,
                )

            notional = trade.quantity * trade.price

            if constraint.constraint_type == "MAX_TRADE_VALUE":
                max_value = Decimal(
                    str(constraint.parameters.get("max_value", "0"))
                )

                if notional > max_value:
                    report.add(
                        "MAX_TRADE_VALUE_EXCEEDED",
                        f"Trade notional {notional} exceeds limit {max_value}.",
                        entity_type="trade",
                        entity_id=trade.trade_id,
                    )

            if constraint.constraint_type == "MIN_TRADE_VALUE":
                min_value = Decimal(
                    str(constraint.parameters.get("min_value", "0"))
                )

                if notional < min_value:
                    report.add(
                        "MIN_TRADE_VALUE_VIOLATED",
                        f"Trade notional {notional} is below limit {min_value}.",
                        entity_type="trade",
                        entity_id=trade.trade_id,
                    )

        matching_schedules = [
            schedule
            for schedule in fee_schedules
            if schedule.effective_from <= as_of_date
            and (
                schedule.effective_to is None
                or schedule.effective_to >= as_of_date
            )
            and (
                schedule.instrument_id == trade.instrument_id
                or schedule.asset_class == instrument.asset_class
                or (
                    schedule.instrument_id is None
                    and schedule.asset_class is None
                )
            )
        ]

        matching_schedules.sort(
            key=lambda schedule: (
                schedule.instrument_id == trade.instrument_id,
                schedule.asset_class == instrument.asset_class,
            ),
            reverse=True,
        )

        if not matching_schedules:
            report.add(
                "MISSING_FEE_SCHEDULE",
                "No applicable fee schedule exists for this trade.",
                entity_type="trade",
                entity_id=trade.trade_id,
            )
        else:
            schedule = matching_schedules[0]
            notional = trade.quantity * trade.price
            expected_fee = max(
                notional * schedule.fee_rate + schedule.fixed_fee,
                schedule.minimum_fee,
            )

            if abs(trade.fees - expected_fee) > FEE_TOLERANCE:
                report.add(
                    "FEE_MISMATCH",
                    f"Recorded fee {trade.fees} differs from expected fee {expected_fee}.",
                    entity_type="trade",
                    entity_id=trade.trade_id,
                )

    return report

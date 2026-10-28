
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_DOWN

from portfolio_rebalancer.calculations.valuation import ValuedHolding, total_market_value
from portfolio_rebalancer.models.constraint import Constraint
from portfolio_rebalancer.models.fee_schedule import FeeSchedule
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.market_price import MarketPrice
from portfolio_rebalancer.rebalancer.constraints import evaluate_trade_constraints
from portfolio_rebalancer.rebalancer.fees import (
    calculate_trade_fee,
    select_fee_schedule,
)


ZERO = Decimal("0")
QUANTITY_STEP = Decimal("0.000001")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class TradeInstruction:
    portfolio_id: str
    instrument_id: str
    side: str
    quantity: Decimal
    price: Decimal
    notional: Decimal
    estimated_fee: Decimal
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RejectedTrade:
    portfolio_id: str
    instrument_id: str
    side: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class TradeSizingResult:
    instructions: tuple[TradeInstruction, ...]
    rejected: tuple[RejectedTrade, ...]


def _floor_quantity(value: Decimal) -> Decimal:
    return value.quantize(QUANTITY_STEP, rounding=ROUND_DOWN)


def size_rebalance_trades(
    portfolio_id: str,
    valued_holdings: list[ValuedHolding],
    target_allocations: dict[str, Decimal],
    instruments: dict[str, Instrument],
    market_prices: dict[str, MarketPrice],
    fee_schedules: list[FeeSchedule],
    constraints: list[Constraint],
    as_of_date: date,
    drift_tolerance: Decimal = Decimal("0.01"),
) -> TradeSizingResult:
    if drift_tolerance < ZERO:
        raise ValueError("drift_tolerance cannot be negative")

    if not valued_holdings:
        raise ValueError("Cannot rebalance a portfolio without valued holdings")

    if any(weight < ZERO for weight in target_allocations.values()):
        raise ValueError("Target weights cannot be negative")

    target_total = sum(target_allocations.values(), ZERO)
    if abs(target_total - Decimal("1")) > Decimal("0.0001"):
        raise ValueError("Target weights must sum to 1.0")

    portfolio_value = total_market_value(valued_holdings)
    if portfolio_value <= ZERO:
        raise ValueError("Portfolio market value must be positive")

    current_values: dict[str, Decimal] = {}
    holdings_by_class: dict[str, list[ValuedHolding]] = {}

    for holding in valued_holdings:
        current_values[holding.asset_class] = (
            current_values.get(holding.asset_class, ZERO)
            + holding.market_value
        )
        holdings_by_class.setdefault(holding.asset_class, []).append(holding)

    actual_classes = set(current_values)
    all_classes = sorted(actual_classes | set(target_allocations))
    actual_weights = {
        asset_class: current_values.get(asset_class, ZERO) / portfolio_value
        for asset_class in all_classes
    }

    instructions: list[TradeInstruction] = []
    rejected: list[RejectedTrade] = []
    remaining_buy_budget: dict[str, Decimal] = {}

    for asset_class in all_classes:
        actual_weight = actual_weights.get(asset_class, ZERO)
        target_weight = target_allocations.get(asset_class, ZERO)
        drift = actual_weight - target_weight

        if drift > drift_tolerance:
            excess_value = (drift * portfolio_value).quantize(CENT)
            positions = sorted(
                holdings_by_class.get(asset_class, []),
                key=lambda item: item.instrument_id,
            )

            for holding in positions:
                if excess_value <= ZERO:
                    break

                instrument = instruments.get(holding.instrument_id)
                if instrument is None:
                    rejected.append(
                        RejectedTrade(
                            portfolio_id,
                            holding.instrument_id,
                            "SELL",
                            ("INSTRUMENT_NOT_FOUND",),
                        )
                    )
                    continue

                price_record = market_prices.get(holding.instrument_id)
                if (
                    price_record is None
                    or price_record.price is None
                    or price_record.price <= ZERO
                    or price_record.quality != "VALID"
                ):
                    rejected.append(
                        RejectedTrade(
                            portfolio_id,
                            holding.instrument_id,
                            "SELL",
                            ("UNUSABLE_MARKET_PRICE",),
                        )
                    )
                    continue

                available_quantity = holding.quantity
                desired_quantity = _floor_quantity(
                    min(excess_value, holding.market_value) / price_record.price
                )
                quantity = min(available_quantity, desired_quantity)

                if quantity <= ZERO:
                    continue

                notional = (quantity * price_record.price).quantize(CENT)
                reasons = evaluate_trade_constraints(
                    portfolio_id,
                    holding.instrument_id,
                    instrument.status,
                    "SELL",
                    notional,
                    as_of_date,
                    constraints,
                )

                if reasons:
                    rejected.append(
                        RejectedTrade(
                            portfolio_id,
                            holding.instrument_id,
                            "SELL",
                            tuple(reasons),
                        )
                    )
                    continue

                try:
                    schedule = select_fee_schedule(
                        fee_schedules,
                        holding.instrument_id,
                        instrument.asset_class,
                        as_of_date,
                    )
                except ValueError:
                    rejected.append(
                        RejectedTrade(
                            portfolio_id,
                            holding.instrument_id,
                            "SELL",
                            ("MISSING_FEE_SCHEDULE",),
                        )
                    )
                    continue

                fee = calculate_trade_fee(notional, schedule)
                instructions.append(
                    TradeInstruction(
                        portfolio_id=portfolio_id,
                        instrument_id=holding.instrument_id,
                        side="SELL",
                        quantity=quantity,
                        price=price_record.price,
                        notional=notional,
                        estimated_fee=fee,
                    )
                )
                excess_value -= notional

        elif drift < -drift_tolerance:
            remaining_buy_budget[asset_class] = (
                (-drift) * portfolio_value
            ).quantize(CENT)

    for asset_class in sorted(remaining_buy_budget):
        remaining = remaining_buy_budget[asset_class]
        existing_instruments = {
            holding.instrument_id
            for holding in holdings_by_class.get(asset_class, [])
        }

        candidates = sorted(
            (
                instrument
                for instrument in instruments.values()
                if instrument.asset_class == asset_class
                and instrument.status == "ACTIVE"
                and instrument.instrument_id in market_prices
            ),
            key=lambda instrument: (
                instrument.instrument_id not in existing_instruments,
                instrument.instrument_id,
            ),
        )

        if not candidates:
            rejected.append(
                RejectedTrade(
                    portfolio_id,
                    "",
                    "BUY",
                    ("NO_ELIGIBLE_INSTRUMENT",),
                )
            )
            continue

        for instrument in candidates:
            if remaining <= ZERO:
                break

            price_record = market_prices[instrument.instrument_id]
            if (
                price_record.price is None
                or price_record.price <= ZERO
                or price_record.quality != "VALID"
            ):
                rejected.append(
                    RejectedTrade(
                        portfolio_id,
                        instrument.instrument_id,
                        "BUY",
                        ("UNUSABLE_MARKET_PRICE",),
                    )
                )
                continue

            try:
                schedule = select_fee_schedule(
                    fee_schedules,
                    instrument.instrument_id,
                    instrument.asset_class,
                    as_of_date,
                )
            except ValueError:
                rejected.append(
                    RejectedTrade(
                        portfolio_id,
                        instrument.instrument_id,
                        "BUY",
                        ("MISSING_FEE_SCHEDULE",),
                    )
                )
                continue

            desired_quantity = _floor_quantity(remaining / price_record.price)
            if desired_quantity <= ZERO:
                continue

            notional = (desired_quantity * price_record.price).quantize(CENT)
            reasons = evaluate_trade_constraints(
                portfolio_id,
                instrument.instrument_id,
                instrument.status,
                "BUY",
                notional,
                as_of_date,
                constraints,
            )

            max_limits = [
                Decimal(str(constraint.parameters.get("max_value", "0")))
                for constraint in constraints
                if constraint.status == "ACTIVE"
                and constraint.constraint_type == "MAX_TRADE_VALUE"
                and constraint.effective_from <= as_of_date
                and (
                    constraint.effective_to is None
                    or constraint.effective_to >= as_of_date
                )
                and (
                    constraint.portfolio_id is None
                    or constraint.portfolio_id == portfolio_id
                )
                and (
                    constraint.instrument_id is None
                    or constraint.instrument_id == instrument.instrument_id
                )
            ]

            if max_limits:
                maximum = min(max_limits)
                if maximum <= ZERO:
                    reasons = sorted(set(reasons + ["MAX_TRADE_VALUE_EXCEEDED"]))
                elif notional > maximum:
                    desired_quantity = _floor_quantity(
                        maximum / price_record.price
                    )
                    notional = (desired_quantity * price_record.price).quantize(CENT)
                    reasons = evaluate_trade_constraints(
                        portfolio_id,
                        instrument.instrument_id,
                        instrument.status,
                        "BUY",
                        notional,
                        as_of_date,
                        constraints,
                    )

            if reasons:
                rejected.append(
                    RejectedTrade(
                        portfolio_id,
                        instrument.instrument_id,
                        "BUY",
                        tuple(reasons),
                    )
                )
                continue

            fee = calculate_trade_fee(notional, schedule)
            instructions.append(
                TradeInstruction(
                    portfolio_id=portfolio_id,
                    instrument_id=instrument.instrument_id,
                    side="BUY",
                    quantity=desired_quantity,
                    price=price_record.price,
                    notional=notional,
                    estimated_fee=fee,
                )
            )
            remaining -= notional

    return TradeSizingResult(
        instructions=tuple(instructions),
        rejected=tuple(rejected),
    )

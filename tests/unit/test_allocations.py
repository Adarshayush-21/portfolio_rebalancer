
from decimal import Decimal

from portfolio_rebalancer.calculations.allocations import calculate_actual_allocations
from portfolio_rebalancer.calculations.drift import calculate_allocation_drift
from portfolio_rebalancer.calculations.valuation import ValuedHolding, total_market_value


def make_holding(
    instrument_id: str,
    asset_class: str,
    market_value: str,
) -> ValuedHolding:
    value = Decimal(market_value)

    return ValuedHolding(
        holding_id=f"HOLD-{instrument_id}",
        portfolio_id="PORT-INV-000001-01",
        instrument_id=instrument_id,
        symbol=instrument_id,
        asset_class=asset_class,
        quantity=Decimal("1"),
        price=value,
        market_value=value,
        price_date=__import__("datetime").date(2026, 10, 22),
    )


def test_total_market_value():
    holdings = [
        make_holding("INS-000001", "EQUITY", "600"),
        make_holding("INS-000002", "BOND", "400"),
    ]

    assert total_market_value(holdings) == Decimal("1000")


def test_actual_allocations_sum_to_one():
    holdings = [
        make_holding("INS-000001", "EQUITY", "600"),
        make_holding("INS-000002", "BOND", "400"),
    ]

    allocations = calculate_actual_allocations(holdings)

    assert allocations["EQUITY"] == Decimal("0.6")
    assert allocations["BOND"] == Decimal("0.4")
    assert sum(allocations.values()) == Decimal("1")


def test_drift_directions():
    drift = calculate_allocation_drift(
        actual_allocations={
            "EQUITY": Decimal("0.70"),
            "BOND": Decimal("0.30"),
        },
        target_allocations={
            "EQUITY": Decimal("0.60"),
            "BOND": Decimal("0.40"),
        },
        tolerance=Decimal("0.01"),
    )

    by_class = {item.asset_class: item for item in drift}

    assert by_class["EQUITY"].recommended_direction == "REDUCE"
    assert by_class["BOND"].recommended_direction == "INCREASE"
    assert by_class["EQUITY"].drift == Decimal("0.10")


def test_missing_actual_class_is_underweight():
    drift = calculate_allocation_drift(
        actual_allocations={"EQUITY": Decimal("1")},
        target_allocations={
            "EQUITY": Decimal("0.8"),
            "BOND": Decimal("0.2"),
        },
    )

    by_class = {item.asset_class: item for item in drift}

    assert by_class["BOND"].actual_weight == Decimal("0")
    assert by_class["BOND"].recommended_direction == "INCREASE"

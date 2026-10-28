
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from portfolio_rebalancer.rebalancer.fees import calculate_trade_fee
from portfolio_rebalancer.rebalancer.trade_sizing import size_rebalance_trades


AS_OF_DATE = date(2026, 10, 22)


def make_instrument(instrument_id, asset_class, status="ACTIVE"):
    return SimpleNamespace(
        instrument_id=instrument_id,
        asset_class=asset_class,
        status=status,
    )


def make_price(price=Decimal("100.00"), quality="VALID"):
    return SimpleNamespace(price=price, quality=quality)


def make_fee_schedule(instrument_id, asset_class):
    return SimpleNamespace(
        instrument_id=instrument_id,
        asset_class=asset_class,
        effective_from=date(2025, 1, 1),
        effective_to=None,
        fee_rate=Decimal("0.001"),
        fixed_fee=Decimal("0"),
        minimum_fee=Decimal("1.00"),
    )


def make_holding(instrument_id, asset_class, quantity, market_value):
    return SimpleNamespace(
        instrument_id=instrument_id,
        asset_class=asset_class,
        quantity=Decimal(str(quantity)),
        market_value=Decimal(str(market_value)),
    )


def test_fee_calculation_applies_minimum():
    schedule = make_fee_schedule("INS-000001", "EQUITY")

    fee = calculate_trade_fee(Decimal("100"), schedule)

    assert fee == Decimal("1.00")


def test_rebalance_sizes_sell_and_buy():
    equity = make_instrument("INS-EQ", "EQUITY")
    bond = make_instrument("INS-BOND", "BOND")

    holdings = [
        make_holding("INS-EQ", "EQUITY", "8", "800"),
        make_holding("INS-BOND", "BOND", "2", "200"),
    ]

    result = size_rebalance_trades(
        portfolio_id="PORT-INV-000001-01",
        valued_holdings=holdings,
        target_allocations={
            "EQUITY": Decimal("0.50"),
            "BOND": Decimal("0.50"),
        },
        instruments={
            "INS-EQ": equity,
            "INS-BOND": bond,
        },
        market_prices={
            "INS-EQ": make_price(),
            "INS-BOND": make_price(),
        },
        fee_schedules=[
            make_fee_schedule("INS-EQ", "EQUITY"),
            make_fee_schedule("INS-BOND", "BOND"),
        ],
        constraints=[],
        as_of_date=AS_OF_DATE,
    )

    trades_by_side = {trade.side: trade for trade in result.instructions}

    assert set(trades_by_side) == {"BUY", "SELL"}
    assert trades_by_side["SELL"].instrument_id == "INS-EQ"
    assert trades_by_side["SELL"].quantity == Decimal("3.000000")
    assert trades_by_side["SELL"].notional == Decimal("300.00")
    assert trades_by_side["BUY"].instrument_id == "INS-BOND"
    assert trades_by_side["BUY"].quantity == Decimal("3.000000")
    assert trades_by_side["BUY"].notional == Decimal("300.00")
    assert all(trade.estimated_fee >= Decimal("0") for trade in result.instructions)


def test_excluded_instrument_is_not_bought():
    equity = make_instrument("INS-EQ", "EQUITY")
    excluded_bond = make_instrument("INS-EXCLUDED", "BOND", status="EXCLUDED")

    result = size_rebalance_trades(
        portfolio_id="PORT-INV-000001-01",
        valued_holdings=[
            make_holding("INS-EQ", "EQUITY", "8", "800"),
        ],
        target_allocations={
            "EQUITY": Decimal("0.50"),
            "BOND": Decimal("0.50"),
        },
        instruments={
            "INS-EQ": equity,
            "INS-EXCLUDED": excluded_bond,
        },
        market_prices={
            "INS-EQ": make_price(),
            "INS-EXCLUDED": make_price(),
        },
        fee_schedules=[
            make_fee_schedule("INS-EQ", "EQUITY"),
            make_fee_schedule("INS-EXCLUDED", "BOND"),
        ],
        constraints=[],
        as_of_date=AS_OF_DATE,
    )

    assert all(
        not (
            trade.side == "BUY"
            and trade.instrument_id == "INS-EXCLUDED"
        )
        for trade in result.instructions
    )
    assert any(
        "NO_ELIGIBLE_INSTRUMENT" in trade.reason_codes
        for trade in result.rejected
    )

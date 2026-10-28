
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_rebalancer.calculations.pricing import get_latest_prices
from portfolio_rebalancer.models.holding import Holding
from portfolio_rebalancer.models.instrument import Instrument


@dataclass(frozen=True)
class ValuedHolding:
    holding_id: str
    portfolio_id: str
    instrument_id: str
    symbol: str
    asset_class: str
    quantity: Decimal
    price: Decimal
    market_value: Decimal
    price_date: date


def value_portfolio(
    session: Session,
    portfolio_id: str,
    as_of_date: date,
    stale_after_days: int = 3,
) -> list[ValuedHolding]:
    holdings = session.scalars(
        select(Holding).where(
            Holding.portfolio_id == portfolio_id,
            Holding.as_of_date == as_of_date,
        )
    ).all()

    if not holdings:
        raise ValueError(
            f"No holdings found for portfolio {portfolio_id} on {as_of_date}"
        )

    instrument_ids = {holding.instrument_id for holding in holdings}

    instruments = session.scalars(
        select(Instrument).where(
            Instrument.instrument_id.in_(instrument_ids)
        )
    ).all()

    instruments_by_id = {
        instrument.instrument_id: instrument for instrument in instruments
    }

    if set(instruments_by_id) != instrument_ids:
        raise ValueError("One or more holdings reference missing instruments")

    prices = get_latest_prices(
        session,
        instrument_ids,
        as_of_date,
        stale_after_days,
    )

    results: list[ValuedHolding] = []

    for holding in holdings:
        instrument = instruments_by_id[holding.instrument_id]
        price_record = prices[holding.instrument_id]
        price = price_record.price

        if price is None:
            raise ValueError(
                f"Market price is missing for {holding.instrument_id}"
            )

        results.append(
            ValuedHolding(
                holding_id=holding.holding_id,
                portfolio_id=holding.portfolio_id,
                instrument_id=holding.instrument_id,
                symbol=instrument.symbol,
                asset_class=instrument.asset_class,
                quantity=holding.quantity,
                price=price,
                market_value=holding.quantity * price,
                price_date=price_record.price_date,
            )
        )

    return results


def total_market_value(valued_holdings: list[ValuedHolding]) -> Decimal:
    return sum(
        (holding.market_value for holding in valued_holdings),
        Decimal("0"),
    )

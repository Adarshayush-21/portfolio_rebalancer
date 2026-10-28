
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_rebalancer.models.market_price import MarketPrice


def get_latest_prices(
    session: Session,
    instrument_ids: set[str],
    as_of_date: date,
    stale_after_days: int = 3,
) -> dict[str, MarketPrice]:
    if stale_after_days < 0:
        raise ValueError("stale_after_days cannot be negative")

    if not instrument_ids:
        return {}

    prices = session.scalars(
        select(MarketPrice)
        .where(
            MarketPrice.instrument_id.in_(instrument_ids),
            MarketPrice.price_date <= as_of_date,
        )
        .order_by(
            MarketPrice.instrument_id,
            MarketPrice.price_date.desc(),
        )
    ).all()

    latest: dict[str, MarketPrice] = {}

    for price in prices:
        latest.setdefault(price.instrument_id, price)

    cutoff = as_of_date - timedelta(days=stale_after_days)

    for instrument_id in instrument_ids:
        price = latest.get(instrument_id)

        if price is None:
            raise ValueError(
                f"No market price available for {instrument_id} on or before {as_of_date}"
            )

        if price.price is None or price.price <= 0:
            raise ValueError(f"Invalid market price for {instrument_id}")

        if price.quality != "VALID":
            raise ValueError(
                f"Market price for {instrument_id} has quality {price.quality}"
            )

        if price.price_date < cutoff:
            raise ValueError(
                f"Market price for {instrument_id} is stale: {price.price_date}"
            )

    return latest

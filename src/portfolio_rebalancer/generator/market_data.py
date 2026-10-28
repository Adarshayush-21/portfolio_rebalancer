
from datetime import date, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_rebalancer.config import DEFAULT_CONFIG, ProjectConfig
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.market_price import MarketPrice


def trading_dates(start_date: str, count: int) -> list[date]:
    current = date.fromisoformat(start_date)
    dates: list[date] = []

    while len(dates) < count:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)

    return dates


def generate_market_data(
    session: Session,
    config: ProjectConfig = DEFAULT_CONFIG,
    batch_size: int = 10_000,
) -> dict[str, int | str]:
    config.validate()

    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    instruments = session.scalars(
        select(Instrument).order_by(Instrument.instrument_id)
    ).all()

    if len(instruments) != config.instrument_count:
        raise ValueError(
            f"Expected {config.instrument_count} instruments, found {len(instruments)}"
        )

    dates = trading_dates(config.start_date, config.trading_days)
    rng = np.random.default_rng((config.seed + 1) % (2**32))

    pending: list[MarketPrice] = []
    row_count = 0

    for instrument_index, instrument in enumerate(instruments):
        initial_price = rng.uniform(10.0, 1000.0)
        daily_returns = rng.normal(
            loc=0.0002,
            scale=0.015,
            size=max(config.trading_days - 1, 0),
        )

        prices = [initial_price]
        for daily_return in daily_returns:
            prices.append(prices[-1] * float(np.exp(daily_return)))

        for price_date, price_value in zip(dates, prices):
            pending.append(
                MarketPrice(
                    price_id=(
                        f"PRICE-{instrument.instrument_id}-"
                        f"{price_date:%Y%m%d}"
                    ),
                    instrument_id=instrument.instrument_id,
                    price_date=price_date,
                    price=f"{price_value:.6f}",
                    quality="VALID",
                    source="SYNTHETIC",
                )
            )

            if len(pending) >= batch_size:
                session.add_all(pending)
                session.flush()
                row_count += len(pending)
                pending.clear()

    if pending:
        session.add_all(pending)
        session.flush()
        row_count += len(pending)

    return {
        "instruments_priced": len(instruments),
        "trading_days": len(dates),
        "market_price_rows": row_count,
        "first_price_date": dates[0].isoformat(),
        "last_price_date": dates[-1].isoformat(),
    }

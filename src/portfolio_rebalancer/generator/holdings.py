
import random
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_rebalancer.config import DEFAULT_CONFIG, ProjectConfig
from portfolio_rebalancer.generator.ids import holding_id
from portfolio_rebalancer.generator.market_data import trading_dates
from portfolio_rebalancer.models.holding import Holding
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.market_price import MarketPrice
from portfolio_rebalancer.models.portfolio import Portfolio
from portfolio_rebalancer.models.target_allocation import TargetAllocation


def _target_weights(asset_classes: list[str], rng: random.Random) -> dict[str, Decimal]:
    unique_classes = sorted(set(asset_classes))
    raw = [rng.uniform(0.1, 1.0) for _ in unique_classes]
    total = sum(raw)

    weights = {
        asset_class: Decimal(str(value / total)).quantize(Decimal("0.000001"))
        for asset_class, value in zip(unique_classes, raw)
    }

    difference = Decimal("1.000000") - sum(weights.values())
    weights[unique_classes[-1]] += difference
    return weights


def generate_holdings_and_targets(
    session: Session,
    config: ProjectConfig = DEFAULT_CONFIG,
) -> dict[str, int | str]:
    config.validate()
    rng = random.Random(config.seed + 2)

    portfolios = session.scalars(
        select(Portfolio).order_by(Portfolio.portfolio_id)
    ).all()
    instruments = session.scalars(
        select(Instrument).order_by(Instrument.instrument_id)
    ).all()

    dates = trading_dates(config.start_date, config.trading_days)
    as_of_date = dates[-1]

    latest_prices = session.scalars(
        select(MarketPrice).where(MarketPrice.price_date == as_of_date)
    ).all()
    prices_by_instrument = {
        price.instrument_id: price for price in latest_prices
    }

    if len(prices_by_instrument) != len(instruments):
        raise ValueError("Latest market prices are incomplete")

    instruments_by_class: dict[str, list[Instrument]] = {}
    for instrument in instruments:
        instruments_by_class.setdefault(instrument.asset_class, []).append(
            instrument
        )

    holdings: list[Holding] = []
    targets: list[TargetAllocation] = []

    for portfolio in portfolios:
        selected_instruments = [
            instrument
            for instrument in instruments
            if rng.random() < min(0.08, 40 / max(len(instruments), 1))
        ]

        if not selected_instruments and instruments:
            selected_instruments = [rng.choice(instruments)]

        for instrument in selected_instruments:
            price = prices_by_instrument[instrument.instrument_id].price
            if price is None or price <= 0:
                raise ValueError(
                    f"Invalid latest price for {instrument.instrument_id}"
                )

            quantity = Decimal(str(rng.randint(1, 100)))
            holdings.append(
                Holding(
                    holding_id=holding_id(
                        portfolio.portfolio_id,
                        instrument.instrument_id,
                    ),
                    portfolio_id=portfolio.portfolio_id,
                    instrument_id=instrument.instrument_id,
                    quantity=quantity,
                    as_of_date=as_of_date,
                )
            )

        weights = _target_weights(
            [instrument.asset_class for instrument in instruments],
            rng,
        )

        for asset_class, weight in weights.items():
            targets.append(
                TargetAllocation(
                    target_id=(
                        f"TGT-{portfolio.portfolio_id}-{asset_class}-"
                        f"{as_of_date:%Y%m%d}"
                    ),
                    portfolio_id=portfolio.portfolio_id,
                    asset_class=asset_class,
                    target_weight=weight,
                    effective_from=as_of_date,
                    effective_to=None,
                )
            )

    session.add_all(holdings)
    session.add_all(targets)
    session.flush()

    return {
        "holdings": len(holdings),
        "target_allocations": len(targets),
        "as_of_date": as_of_date.isoformat(),
    }


from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_rebalancer.models.holding import Holding
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.market_price import MarketPrice
from portfolio_rebalancer.models.post_trade_position import PostTradePosition
from portfolio_rebalancer.models.rebalance_proposal import RebalanceProposal
from portfolio_rebalancer.models.trade import Trade


ZERO = Decimal("0")


def calculate_post_trade_snapshot(
    session: Session,
    proposal_id: str,
    execution_date: date | None = None,
    trades: list[Trade] | None = None,
    stale_after_days: int = 3,
) -> dict:
    proposal = session.get(RebalanceProposal, proposal_id)
    if proposal is None:
        raise ValueError(f"Proposal not found: {proposal_id}")

    effective_date = execution_date or proposal.as_of_date

    if effective_date < proposal.as_of_date:
        raise ValueError("Execution date cannot precede proposal date")

    holdings = session.scalars(
        select(Holding).where(
            Holding.portfolio_id == proposal.portfolio_id,
            Holding.as_of_date == proposal.as_of_date,
        )
    ).all()

    if not holdings:
        raise ValueError(
            f"No holdings found for portfolio {proposal.portfolio_id} "
            f"on {proposal.as_of_date}"
        )

    if trades is None:
        trades = session.scalars(
            select(Trade).where(
                Trade.proposal_id == proposal_id,
                Trade.status.in_(["PROPOSED", "APPROVED", "EXECUTED"]),
            )
        ).all()

    quantities = {
        holding.instrument_id: holding.quantity
        for holding in holdings
    }

    instrument_ids = set(quantities)
    instrument_ids.update(trade.instrument_id for trade in trades)

    instruments_list = session.scalars(
        select(Instrument).where(
            Instrument.instrument_id.in_(instrument_ids)
        )
    ).all()

    instruments = {
        instrument.instrument_id: instrument
        for instrument in instruments_list
    }

    if set(instruments) != instrument_ids:
        raise ValueError("A holding or trade references a missing instrument")

    latest_prices = {}
    price_records = session.scalars(
        select(MarketPrice)
        .where(
            MarketPrice.instrument_id.in_(instrument_ids),
            MarketPrice.price_date <= effective_date,
        )
        .order_by(
            MarketPrice.instrument_id,
            MarketPrice.price_date.desc(),
        )
    ).all()

    for record in price_records:
        latest_prices.setdefault(record.instrument_id, record)

    positions = []
    total_value = ZERO
    values_by_class = defaultdict(lambda: ZERO)

    for instrument_id in sorted(instrument_ids):
        quantity = quantities.get(instrument_id, ZERO)

        for trade in trades:
            if trade.instrument_id != instrument_id:
                continue

            if trade.side == "BUY":
                if instruments[instrument_id].status == "EXCLUDED":
                    raise ValueError(
                        f"Cannot buy excluded instrument {instrument_id}"
                    )
                quantity += trade.quantity
            elif trade.side == "SELL":
                quantity -= trade.quantity
            else:
                raise ValueError(f"Unsupported trade side: {trade.side}")

        if quantity < ZERO:
            raise ValueError(
                f"Post-trade quantity would be negative for {instrument_id}"
            )

        price_record = latest_prices.get(instrument_id)
        if price_record is None:
            raise ValueError(f"No market price for {instrument_id}")

        if price_record.quality != "VALID" or price_record.price is None:
            raise ValueError(
                f"Latest market price for {instrument_id} is "
                f"{price_record.quality}; refusing silent use"
            )

        price_age = (effective_date - price_record.price_date).days
        if price_age > stale_after_days:
            raise ValueError(
                f"Market price for {instrument_id} is {price_age} days old"
            )

        market_value = quantity * price_record.price
        asset_class = instruments[instrument_id].asset_class

        total_value += market_value
        values_by_class[asset_class] += market_value

        positions.append(
            {
                "instrument_id": instrument_id,
                "asset_class": asset_class,
                "quantity": str(quantity),
                "price": str(price_record.price),
                "price_date": price_record.price_date.isoformat(),
                "market_value": str(market_value),
            }
        )

    if total_value <= ZERO:
        raise ValueError("Post-trade portfolio value must be positive")

    allocations = {
        asset_class: str(value / total_value)
        for asset_class, value in sorted(values_by_class.items())
    }

    trade_notionals = [
        (trade.quantity * trade.price).quantize(Decimal("0.01"))
        for trade in trades
    ]
    turnover = sum(trade_notionals, ZERO)
    total_fees = sum((trade.fees for trade in trades), ZERO)

    signed_trade_value = sum(
        (
            notional if trade.side == "SELL" else -notional
        )
        for trade, notional in zip(trades, trade_notionals)
    )
    net_cash_flow = signed_trade_value - total_fees

    return {
        "proposal_id": proposal_id,
        "portfolio_id": proposal.portfolio_id,
        "source_as_of_date": proposal.as_of_date.isoformat(),
        "valuation_date": effective_date.isoformat(),
        "position_count": len(positions),
        "total_market_value": str(total_value),
        "estimated_turnover": str(turnover),
        "total_fees": str(total_fees),
        "net_cash_flow_from_trades": str(net_cash_flow),
        "post_trade_allocations": allocations,
        "positions": positions,
    }


def persist_post_trade_snapshot(
    session: Session,
    snapshot: dict,
) -> list[PostTradePosition]:
    proposal_id = snapshot["proposal_id"]
    valuation_date = date.fromisoformat(snapshot["valuation_date"])

    existing = session.scalars(
        select(PostTradePosition.position_id).where(
            PostTradePosition.proposal_id == proposal_id
        )
    ).first()

    if existing is not None:
        raise ValueError(
            f"Post-trade positions already exist for proposal {proposal_id}"
        )

    persisted_positions = []

    for position in snapshot["positions"]:
        instrument_id = position["instrument_id"]
        position_id = f"PTP-{proposal_id}-{instrument_id}"

        record = PostTradePosition(
            position_id=position_id,
            proposal_id=proposal_id,
            instrument_id=instrument_id,
            quantity=Decimal(position["quantity"]),
            valuation_price=Decimal(position["price"]),
            market_value=Decimal(position["market_value"]),
            asset_class=position["asset_class"],
            valuation_date=valuation_date,
        )
        session.add(record)
        persisted_positions.append(record)

    session.flush()
    return persisted_positions

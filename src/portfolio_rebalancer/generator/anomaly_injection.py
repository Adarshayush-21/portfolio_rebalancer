
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from portfolio_rebalancer.config import DEFAULT_CONFIG, ProjectConfig
from portfolio_rebalancer.generator.market_data import trading_dates
from portfolio_rebalancer.models.constraint import Constraint
from portfolio_rebalancer.models.fee_schedule import FeeSchedule
from portfolio_rebalancer.models.holding import Holding
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.market_price import MarketPrice
from portfolio_rebalancer.models.rebalance_proposal import RebalanceProposal
from portfolio_rebalancer.models.target_allocation import TargetAllocation
from portfolio_rebalancer.models.trade import Trade
from portfolio_rebalancer.rebalancer.fees import (
    calculate_trade_fee,
    select_fee_schedule,
)


CENT = Decimal("0.01")
ZERO = Decimal("0")


def _latest_price(
    session: Session,
    instrument_id: str,
    as_of_date: date,
) -> MarketPrice | None:
    return session.scalars(
        select(MarketPrice)
        .where(
            MarketPrice.instrument_id == instrument_id,
            MarketPrice.price_date <= as_of_date,
        )
        .order_by(MarketPrice.price_date.desc())
    ).first()


def _trade_fee(
    session: Session,
    instrument_id: str,
    quantity: Decimal,
    price: Decimal,
    as_of_date: date,
) -> Decimal:
    instrument = session.get(Instrument, instrument_id)
    if instrument is None:
        raise ValueError(f"Instrument not found: {instrument_id}")

    schedules = session.scalars(
        select(FeeSchedule).where(
            FeeSchedule.effective_from <= as_of_date,
            (
                FeeSchedule.effective_to.is_(None)
                | (FeeSchedule.effective_to >= as_of_date)
            ),
        )
    ).all()

    schedule = select_fee_schedule(
        schedules,
        instrument_id,
        instrument.asset_class,
        as_of_date,
    )
    notional = (quantity * price).quantize(CENT)
    return calculate_trade_fee(notional, schedule)


def _create_proposal(
    session: Session,
    proposal_id: str,
    portfolio_id: str,
    as_of_date: date,
    rationale: str,
) -> RebalanceProposal:
    proposal = RebalanceProposal(
        proposal_id=proposal_id,
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        status="DRAFT",
        estimated_turnover=ZERO,
        total_fees=ZERO,
        created_at=datetime.combine(
            as_of_date,
            time.min,
            tzinfo=timezone.utc,
        ),
        rationale=rationale,
    )
    session.add(proposal)
    session.flush()
    return proposal


def _create_trade(
    session: Session,
    trade_id: str,
    proposal_id: str,
    instrument_id: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    fees: Decimal,
    reason_code: str,
) -> None:
    session.add(
        Trade(
            trade_id=trade_id,
            proposal_id=proposal_id,
            instrument_id=instrument_id,
            side=side,
            quantity=quantity,
            price=price,
            fees=fees,
            status="PROPOSED",
            reason_codes=[reason_code],
        )
    )


def _latest_usable_price(
    session: Session,
    instrument_id: str,
    as_of_date: date,
) -> MarketPrice | None:
    price = _latest_price(session, instrument_id, as_of_date)
    if (
        price is None
        or price.price is None
        or price.price <= ZERO
        or price.quality != "VALID"
    ):
        return None
    return price


def _holdings_per_instrument(
    holdings: list[Holding],
    as_of_date: date,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for holding in holdings:
        if holding.as_of_date == as_of_date:
            counts[holding.instrument_id] = (
                counts.get(holding.instrument_id, 0) + 1
            )
    return counts


def inject_anomalies(
    session: Session,
    config: ProjectConfig = DEFAULT_CONFIG,
) -> list[dict[str, str]]:
    config.validate()
    labels: list[dict[str, str]] = []

    as_of_date = trading_dates(
        config.start_date,
        config.trading_days,
    )[-1]

    holdings = session.scalars(
        select(Holding).order_by(Holding.holding_id)
    ).all()
    instruments = session.scalars(
        select(Instrument).order_by(Instrument.instrument_id)
    ).all()

    if not holdings:
        raise ValueError("No holdings exist for anomaly injection")
    if not instruments:
        raise ValueError("No instruments exist for anomaly injection")

    holdings_by_instrument = _holdings_per_instrument(
        holdings,
        as_of_date,
    )

    # 1. Target weights do not sum to 100%.
    target = session.scalars(
        select(TargetAllocation).order_by(TargetAllocation.target_id)
    ).first()

    if target is None:
        raise ValueError("No target allocation exists")

    target.target_weight = (
        target.target_weight + Decimal("0.05")
        if target.target_weight <= Decimal("0.95")
        else Decimal("0.90")
    )

    labels.append(
        {
            "anomaly_id": "ANOM-000001",
            "anomaly_type": "TARGET_WEIGHTS_NOT_100_PERCENT",
            "entity_type": "portfolio",
            "entity_id": target.portfolio_id,
            "expected_detection": "TARGET_WEIGHTS_NOT_100_PERCENT",
        }
    )

    # 2. Mark a uniquely held instrument's latest price as stale when possible.
    stale_holding = next(
        (
            holding
            for holding in holdings
            if holding.as_of_date == as_of_date
            and holdings_by_instrument.get(holding.instrument_id) == 1
        ),
        None,
    )

    if stale_holding is None:
        stale_holding = next(
            (h for h in holdings if h.as_of_date == as_of_date),
            None,
        )

    if stale_holding is None:
        raise ValueError("No holding exists on the validation date")

    stale_price = _latest_price(
        session,
        stale_holding.instrument_id,
        as_of_date,
    )
    if stale_price is None:
        raise ValueError("No market price exists for stale-price injection")

    stale_price.quality = "STALE"

    labels.append(
        {
            "anomaly_id": "ANOM-000002",
            "anomaly_type": "STALE_MARKET_PRICE",
            "entity_type": "holding",
            "entity_id": stale_holding.holding_id,
            "expected_detection": "STALE_MARKET_PRICE",
        }
    )

    # 3. Remove one instrument-specific fee schedule.
    fee_schedule = session.scalars(
        select(FeeSchedule)
        .where(FeeSchedule.instrument_id.is_not(None))
        .order_by(FeeSchedule.fee_schedule_id)
    ).first()

    if fee_schedule is None:
        raise ValueError("No instrument-specific fee schedule exists")

    missing_fee_instrument_id = fee_schedule.instrument_id
    if missing_fee_instrument_id is None:
        raise ValueError("Selected fee schedule has no instrument")

    session.delete(fee_schedule)
    session.flush()

    labels.append(
        {
            "anomaly_id": "ANOM-000003",
            "anomaly_type": "MISSING_FEE_SCHEDULE",
            "entity_type": "instrument",
            "entity_id": missing_fee_instrument_id,
            "expected_detection": "MISSING_FEE_SCHEDULE",
        }
    )

    # 4. Recommend selling more units than the portfolio holds.
    oversell_holding = None
    oversell_price = None

    for candidate in holdings:
        if candidate.as_of_date != as_of_date or candidate.quantity <= ZERO:
            continue
        if candidate.instrument_id in {
            stale_holding.instrument_id,
            missing_fee_instrument_id,
        }:
            continue

        candidate_price = _latest_usable_price(
            session,
            candidate.instrument_id,
            as_of_date,
        )
        if candidate_price is None:
            continue

        candidate_instrument = session.get(
            Instrument,
            candidate.instrument_id,
        )
        if candidate_instrument is None:
            continue

        try:
            _trade_fee(
                session,
                candidate.instrument_id,
                candidate.quantity + Decimal("1"),
                candidate_price.price,
                as_of_date,
            )
        except ValueError:
            continue

        oversell_holding = candidate
        oversell_price = candidate_price
        break

    if oversell_holding is None or oversell_price is None:
        raise ValueError(
            "Could not find a separate holding with a valid price "
            "and applicable fee schedule for oversell injection"
        )

    oversell_quantity = oversell_holding.quantity + Decimal("1")
    oversell_fee = _trade_fee(
        session,
        oversell_holding.instrument_id,
        oversell_quantity,
        oversell_price.price,
        as_of_date,
    )

    proposal = _create_proposal(
        session,
        "RB-2026-ANOM-000004",
        oversell_holding.portfolio_id,
        as_of_date,
        "Ground-truth anomaly: sell quantity exceeds available holding",
    )
    _create_trade(
        session,
        "TR-ANOM-000004",
        proposal.proposal_id,
        oversell_holding.instrument_id,
        "SELL",
        oversell_quantity,
        oversell_price.price,
        oversell_fee,
        "ANOMALY_OVERSOLD_POSITION",
    )

    labels.append(
        {
            "anomaly_id": "ANOM-000004",
            "anomaly_type": "TRADE_EXCEEDS_HOLDING",
            "entity_type": "trade",
            "entity_id": "TR-ANOM-000004",
            "expected_detection": "TRADE_EXCEEDS_HOLDING",
        }
    )

    # 5. Recommend buying an excluded instrument.
    excluded_candidate = next(
        (
            h
            for h in holdings
            if h.as_of_date == as_of_date
            and h.instrument_id
            not in {
                stale_holding.instrument_id,
                oversell_holding.instrument_id,
                missing_fee_instrument_id,
            }
            and _latest_usable_price(
                session,
                h.instrument_id,
                as_of_date,
            )
            is not None
        ),
        None,
    )

    if excluded_candidate is None:
        raise ValueError(
            "Could not find a separate holding with a valid price "
            "for excluded-instrument injection"
        )

    excluded_instrument = session.get(
        Instrument,
        excluded_candidate.instrument_id,
    )
    if excluded_instrument is None:
        raise ValueError("Selected excluded instrument does not exist")

    excluded_price = _latest_usable_price(
        session,
        excluded_candidate.instrument_id,
        as_of_date,
    )
    if excluded_price is None or excluded_price.price is None:
        raise ValueError("No usable price exists for excluded-instrument injection")

    excluded_fee = _trade_fee(
        session,
        excluded_candidate.instrument_id,
        Decimal("1"),
        excluded_price.price,
        as_of_date,
    )

    excluded_instrument.status = "EXCLUDED"

    proposal = _create_proposal(
        session,
        "RB-2026-ANOM-000005",
        excluded_candidate.portfolio_id,
        as_of_date,
        "Ground-truth anomaly: buy an excluded instrument",
    )
    _create_trade(
        session,
        "TR-ANOM-000005",
        proposal.proposal_id,
        excluded_candidate.instrument_id,
        "BUY",
        Decimal("1"),
        excluded_price.price,
        excluded_fee,
        "ANOMALY_EXCLUDED_INSTRUMENT",
    )

    labels.append(
        {
            "anomaly_id": "ANOM-000005",
            "anomaly_type": "EXCLUDED_INSTRUMENT_RECOMMENDED",
            "entity_type": "trade",
            "entity_id": "TR-ANOM-000005",
            "expected_detection": "BUY_EXCLUDED_INSTRUMENT",
        }
    )

    # 6. Remove newer VALID prices so an old price is used without a stale flag.
    age_cutoff = as_of_date - timedelta(days=5)
    stale_use_holding = None
    stale_use_price = None

    excluded_instrument_ids = {
        stale_holding.instrument_id,
        oversell_holding.instrument_id,
        excluded_candidate.instrument_id,
        missing_fee_instrument_id,
    }

    for candidate in holdings:
        if candidate.as_of_date != as_of_date:
            continue
        if candidate.instrument_id in excluded_instrument_ids:
            continue
        if holdings_by_instrument.get(candidate.instrument_id) != 1:
            continue

        prices = session.scalars(
            select(MarketPrice)
            .where(MarketPrice.instrument_id == candidate.instrument_id)
            .order_by(MarketPrice.price_date.desc())
        ).all()

        retained_prices = [
            price
            for price in prices
            if price.price_date <= age_cutoff
            and price.price is not None
            and price.price > ZERO
            and price.quality == "VALID"
        ]

        newer_prices = [
            price
            for price in prices
            if age_cutoff < price.price_date <= as_of_date
            and price.price is not None
            and price.price > ZERO
            and price.quality == "VALID"
        ]
        if not retained_prices or not newer_prices:
            continue

        stale_candidate = retained_prices[0]
        latest_newer_price = max(
            newer_prices,
            key=lambda price: price.price_date,
        )
        if latest_newer_price.price == stale_candidate.price:
            continue

        stale_use_holding = candidate
        stale_use_price = stale_candidate
        break

    if stale_use_holding is None or stale_use_price is None:
        raise ValueError(
            "Could not find a uniquely held instrument with a valid older price "
            "and newer prices for stale-price-age injection"
        )

    session.flush()

    stale_use_fee = _trade_fee(
        session,
        stale_use_holding.instrument_id,
        Decimal("1"),
        stale_use_price.price,
        as_of_date,
    )

    proposal = _create_proposal(
        session,
        "RB-2026-ANOM-000006",
        stale_use_holding.portfolio_id,
        as_of_date,
        "Ground-truth anomaly: use an old price without a stale-price warning",
    )
    _create_trade(
        session,
        "TR-ANOM-000006",
        proposal.proposal_id,
        stale_use_holding.instrument_id,
        "BUY",
        Decimal("1"),
        stale_use_price.price,
        stale_use_fee,
        "ANOMALY_STALE_PRICE_USED",
    )

    labels.append(
        {
            "anomaly_id": "ANOM-000006",
            "anomaly_type": "STALE_PRICE_USED_WITHOUT_WARNING",
            "entity_type": "trade",
            "entity_id": "TR-ANOM-000006",
            "expected_detection": "STALE_TRADE_PRICE",
        }
    )

    session.flush()
    return labels


import re
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from portfolio_rebalancer.calculations.allocations import (
    calculate_actual_allocations,
    get_active_target_allocations,
)
from portfolio_rebalancer.calculations.drift import calculate_allocation_drift
from portfolio_rebalancer.calculations.valuation import value_portfolio
from portfolio_rebalancer.models.constraint import Constraint
from portfolio_rebalancer.models.fee_schedule import FeeSchedule
from portfolio_rebalancer.models.holding import Holding
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.market_price import MarketPrice
from portfolio_rebalancer.models.portfolio import Portfolio
from portfolio_rebalancer.models.rebalance_proposal import RebalanceProposal
from portfolio_rebalancer.rebalancer.decision_receipts import (
    persist_decision_receipts,
)
from portfolio_rebalancer.rebalancer.proposals import (
    persist_rebalance_proposal,
)
from portfolio_rebalancer.rebalancer.trade_sizing import (
    size_rebalance_trades,
)


def _resolve_as_of_date(
    session: Session,
    portfolio_id: str,
    requested_date: date | None,
) -> date:
    if requested_date is not None:
        return requested_date

    latest_date = session.scalar(
        select(func.max(Holding.as_of_date)).where(
            Holding.portfolio_id == portfolio_id
        )
    )

    if latest_date is None:
        raise ValueError(
            f"No holdings exist for portfolio {portfolio_id}"
        )

    return latest_date


def _next_proposal_id(
    session: Session,
    as_of_date: date,
) -> str:
    prefix = f"RB-{as_of_date.year}-"
    existing = set(
        session.scalars(
            select(RebalanceProposal.proposal_id).where(
                RebalanceProposal.proposal_id.like(f"{prefix}%")
            )
        ).all()
    )

    number = 1
    while f"{prefix}{number:06d}" in existing:
        number += 1

    return f"{prefix}{number:06d}"


def _latest_prices(
    session: Session,
    as_of_date: date,
) -> dict[str, MarketPrice]:
    records = session.scalars(
        select(MarketPrice)
        .where(MarketPrice.price_date <= as_of_date)
        .order_by(
            MarketPrice.instrument_id,
            MarketPrice.price_date.desc(),
        )
    ).all()

    latest: dict[str, MarketPrice] = {}
    for record in records:
        latest.setdefault(record.instrument_id, record)

    return latest


def run_rebalancing(
    session: Session,
    portfolio_id: str,
    as_of_date: date | None = None,
    proposal_id: str | None = None,
    drift_tolerance: Decimal = Decimal("0.01"),
) -> dict:
    portfolio = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise ValueError(f"Portfolio not found: {portfolio_id}")

    if portfolio.status != "ACTIVE":
        raise ValueError(
            f"Portfolio {portfolio_id} is not active"
        )

    effective_date = _resolve_as_of_date(
        session,
        portfolio_id,
        as_of_date,
    )

    valued_holdings = value_portfolio(
        session,
        portfolio_id,
        effective_date,
    )

    actual_allocations = calculate_actual_allocations(
        valued_holdings
    )
    target_allocations = get_active_target_allocations(
        session,
        portfolio_id,
        effective_date,
    )
    drift = calculate_allocation_drift(
        actual_allocations,
        target_allocations,
        drift_tolerance,
    )

    instruments_list = session.scalars(
        select(Instrument)
    ).all()
    instruments = {
        instrument.instrument_id: instrument
        for instrument in instruments_list
    }

    prices = _latest_prices(session, effective_date)

    fee_schedules = session.scalars(
        select(FeeSchedule).where(
            FeeSchedule.effective_from <= effective_date,
            or_(
                FeeSchedule.effective_to.is_(None),
                FeeSchedule.effective_to >= effective_date,
            ),
        )
    ).all()

    constraints = session.scalars(
        select(Constraint).where(
            Constraint.status == "ACTIVE",
            Constraint.effective_from <= effective_date,
            or_(
                Constraint.effective_to.is_(None),
                Constraint.effective_to >= effective_date,
            ),
        )
    ).all()

    sizing_result = size_rebalance_trades(
        portfolio_id=portfolio_id,
        valued_holdings=valued_holdings,
        target_allocations=target_allocations,
        instruments=instruments,
        market_prices=prices,
        fee_schedules=fee_schedules,
        constraints=constraints,
        as_of_date=effective_date,
        drift_tolerance=drift_tolerance,
    )

    resolved_proposal_id = (
        proposal_id or _next_proposal_id(session, effective_date)
    )

    if not re.fullmatch(
        r"RB-\d{4}-\d{6}",
        resolved_proposal_id,
    ):
        raise ValueError(
            "proposal_id must use the format RB-YYYY-NNNNNN"
        )

    if session.get(RebalanceProposal, resolved_proposal_id) is not None:
        raise ValueError(
            f"Proposal already exists: {resolved_proposal_id}"
        )

    proposal = persist_rebalance_proposal(
        session=session,
        proposal_id=resolved_proposal_id,
        portfolio_id=portfolio_id,
        as_of_date=effective_date,
        sizing_result=sizing_result,
        rationale="Policy-constrained portfolio rebalance",
    )

    receipts = persist_decision_receipts(
        session=session,
        proposal_id=resolved_proposal_id,
        portfolio_id=portfolio_id,
        as_of_date=effective_date,
        sizing_result=sizing_result,
    )

    return {
        "proposal_id": proposal.proposal_id,
        "portfolio_id": portfolio_id,
        "as_of_date": effective_date.isoformat(),
        "status": proposal.status,
        "total_market_value": str(
            sum(
                (holding.market_value for holding in valued_holdings),
                Decimal("0"),
            )
        ),
        "actual_allocations": {
            key: str(value)
            for key, value in sorted(actual_allocations.items())
        },
        "target_allocations": {
            key: str(value)
            for key, value in sorted(target_allocations.items())
        },
        "allocation_drift": [
            {
                "asset_class": item.asset_class,
                "actual_weight": str(item.actual_weight),
                "target_weight": str(item.target_weight),
                "drift": str(item.drift),
                "recommended_direction": item.recommended_direction,
            }
            for item in drift
        ],
        "trade_count": len(sizing_result.instructions),
        "rejected_decision_count": len(sizing_result.rejected),
        "receipt_count": len(receipts),
        "estimated_turnover": str(proposal.estimated_turnover),
        "total_fees": str(proposal.total_fees),
        "trades": [
            {
                "instrument_id": item.instrument_id,
                "side": item.side,
                "quantity": str(item.quantity),
                "price": str(item.price),
                "notional": str(item.notional),
                "estimated_fee": str(item.estimated_fee),
                "reason_codes": list(item.reason_codes),
            }
            for item in sizing_result.instructions
        ],
        "rejected_decisions": [
            {
                "instrument_id": item.instrument_id,
                "side": item.side,
                "reason_codes": list(item.reason_codes),
            }
            for item in sizing_result.rejected
        ],
    }

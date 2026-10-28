
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_rebalancer.models.rebalance_proposal import RebalanceProposal
from portfolio_rebalancer.models.trade import Trade
from portfolio_rebalancer.simulation.event_log import append_simulation_event
from portfolio_rebalancer.simulation.post_trade import (
    calculate_post_trade_snapshot,
    persist_post_trade_snapshot,
)


EXECUTABLE_PROPOSAL_STATUSES = {"DRAFT", "VALIDATED", "APPROVED"}
EXECUTABLE_TRADE_STATUSES = {"PROPOSED", "APPROVED"}


def simulate_proposal_execution(
    session: Session,
    proposal_id: str,
    execution_date: date | None = None,
    stale_after_days: int = 3,
) -> dict:
    proposal = session.get(RebalanceProposal, proposal_id)

    if proposal is None:
        raise ValueError(f"Proposal not found: {proposal_id}")

    if proposal.status not in EXECUTABLE_PROPOSAL_STATUSES:
        raise ValueError(
            f"Proposal {proposal_id} cannot be simulated from status "
            f"{proposal.status}"
        )

    trades = session.scalars(
        select(Trade)
        .where(
            Trade.proposal_id == proposal_id,
            Trade.status.in_(EXECUTABLE_TRADE_STATUSES),
        )
        .order_by(Trade.trade_id)
    ).all()

    if not trades:
        raise ValueError(f"No executable trades found for {proposal_id}")

    snapshot = calculate_post_trade_snapshot(
        session=session,
        proposal_id=proposal_id,
        execution_date=execution_date,
        trades=trades,
        stale_after_days=stale_after_days,
    )

    persisted_positions = persist_post_trade_snapshot(
        session=session,
        snapshot=snapshot,
    )

    for trade in trades:
        trade.status = "EXECUTED"

        append_simulation_event(
            session=session,
            event_type="SIMULATED_TRADE_EXECUTED",
            entity_type="TRADE",
            entity_id=trade.trade_id,
            correlation_id=proposal_id,
            payload={
                "proposal_id": proposal_id,
                "instrument_id": trade.instrument_id,
                "side": trade.side,
                "quantity": str(trade.quantity),
                "price": str(trade.price),
                "fees": str(trade.fees),
                "execution_date": snapshot["valuation_date"],
                "simulation_only": True,
            },
        )

    proposal.status = "EXECUTED"

    append_simulation_event(
        session=session,
        event_type="POST_TRADE_SNAPSHOT_CREATED",
        entity_type="REBALANCE_PROPOSAL",
        entity_id=proposal_id,
        correlation_id=proposal_id,
        payload={
            **snapshot,
            "persisted_position_count": len(persisted_positions),
        },
    )

    append_simulation_event(
        session=session,
        event_type="SIMULATED_EXECUTION_COMPLETED",
        entity_type="REBALANCE_PROPOSAL",
        entity_id=proposal_id,
        correlation_id=proposal_id,
        payload={
            "trade_count": len(trades),
            "persisted_position_count": len(persisted_positions),
            "total_fees": snapshot["total_fees"],
            "estimated_turnover": snapshot["estimated_turnover"],
            "total_market_value": snapshot["total_market_value"],
            "simulation_only": True,
        },
    )

    session.flush()

    return {
        "proposal_id": proposal_id,
        "status": proposal.status,
        "simulation_only": True,
        "trade_count": len(trades),
        "persisted_position_count": len(persisted_positions),
        "post_trade_snapshot": snapshot,
    }

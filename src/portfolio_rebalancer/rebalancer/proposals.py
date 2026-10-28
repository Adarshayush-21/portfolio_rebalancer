
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from portfolio_rebalancer.models.rebalance_proposal import RebalanceProposal
from portfolio_rebalancer.models.trade import Trade
from portfolio_rebalancer.rebalancer.trade_sizing import TradeSizingResult


ZERO = Decimal("0")


def persist_rebalance_proposal(
    session: Session,
    proposal_id: str,
    portfolio_id: str,
    as_of_date: date,
    sizing_result: TradeSizingResult,
    rationale: str = "Policy-constrained portfolio rebalance",
) -> RebalanceProposal:
    if not proposal_id.strip():
        raise ValueError("proposal_id cannot be empty")

    if not portfolio_id.strip():
        raise ValueError("portfolio_id cannot be empty")

    if not isinstance(as_of_date, date):
        raise ValueError("as_of_date must be a date")

    if not rationale.strip():
        raise ValueError("rationale cannot be empty")

    instructions = sizing_result.instructions

    for instruction in instructions:
        if instruction.portfolio_id != portfolio_id:
            raise ValueError("All trade instructions must match portfolio_id")
        if instruction.quantity <= ZERO:
            raise ValueError("Trade quantity must be positive")
        if instruction.price <= ZERO:
            raise ValueError("Trade price must be positive")
        if instruction.notional < ZERO:
            raise ValueError("Trade notional cannot be negative")
        if instruction.estimated_fee < ZERO:
            raise ValueError("Trade fees cannot be negative")
        if instruction.side not in {"BUY", "SELL"}:
            raise ValueError("Trade side must be BUY or SELL")

    total_turnover = sum(
        (instruction.notional for instruction in instructions),
        ZERO,
    )
    total_fees = sum(
        (instruction.estimated_fee for instruction in instructions),
        ZERO,
    )

    proposal = RebalanceProposal(
        proposal_id=proposal_id,
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        status="DRAFT",
        estimated_turnover=total_turnover,
        total_fees=total_fees,
        rationale=rationale,
    )

    proposal.trades = [
        Trade(
            trade_id=f"TRD-{proposal_id}-{index:04d}",
            proposal_id=proposal_id,
            instrument_id=instruction.instrument_id,
            side=instruction.side,
            quantity=instruction.quantity,
            price=instruction.price,
            fees=instruction.estimated_fee,
            status="PROPOSED",
            reason_codes=list(instruction.reason_codes),
        )
        for index, instruction in enumerate(instructions, start=1)
    ]

    session.add(proposal)
    session.flush()

    return proposal

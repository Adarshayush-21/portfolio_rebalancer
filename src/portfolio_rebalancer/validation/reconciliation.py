
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_rebalancer.models.holding import Holding
from portfolio_rebalancer.models.rebalance_proposal import RebalanceProposal
from portfolio_rebalancer.models.trade import Trade
from portfolio_rebalancer.validation.report import ValidationReport


ZERO = Decimal("0")
TOLERANCE = Decimal("0.01")


def validate_reconciliation(
    session: Session,
    as_of_date,
) -> ValidationReport:
    report = ValidationReport()

    proposals = session.scalars(
        select(RebalanceProposal).where(
            RebalanceProposal.as_of_date == as_of_date
        )
    ).all()

    trades = session.scalars(
        select(Trade).join(
            RebalanceProposal,
            Trade.proposal_id == RebalanceProposal.proposal_id,
        ).where(
            RebalanceProposal.as_of_date == as_of_date,
            Trade.status.in_(["PROPOSED", "APPROVED", "EXECUTED"]),
        )
    ).all()

    holdings = session.scalars(
        select(Holding).where(Holding.as_of_date == as_of_date)
    ).all()

    trades_by_proposal = defaultdict(list)
    for trade in trades:
        trades_by_proposal[trade.proposal_id].append(trade)

    holdings_by_portfolio_instrument = defaultdict(lambda: ZERO)
    for holding in holdings:
        key = (holding.portfolio_id, holding.instrument_id)
        holdings_by_portfolio_instrument[key] += holding.quantity

    report.checks_run += 1

    for proposal in proposals:
        proposal_trades = trades_by_proposal.get(proposal.proposal_id, [])

        calculated_fees = sum(
            (trade.fees for trade in proposal_trades), ZERO
        )
        if abs(calculated_fees - proposal.total_fees) > TOLERANCE:
            report.add(
                "PROPOSAL_FEE_RECONCILIATION_FAILURE",
                f"Proposal fees are {proposal.total_fees}; trade fees total "
                f"{calculated_fees}.",
                entity_type="proposal",
                entity_id=proposal.proposal_id,
            )

        calculated_turnover = sum(
            (trade.quantity * trade.price for trade in proposal_trades),
            ZERO,
        )
        if abs(calculated_turnover - proposal.estimated_turnover) > TOLERANCE:
            report.add(
                "PROPOSAL_TURNOVER_RECONCILIATION_FAILURE",
                f"Proposal turnover is {proposal.estimated_turnover}; trade "
                f"notional totals {calculated_turnover}.",
                entity_type="proposal",
                entity_id=proposal.proposal_id,
            )

        sold_quantities = defaultdict(lambda: ZERO)
        for trade in proposal_trades:
            if trade.side == "SELL":
                sold_quantities[trade.instrument_id] += trade.quantity

        for instrument_id, sold_quantity in sold_quantities.items():
            available_quantity = holdings_by_portfolio_instrument.get(
                (proposal.portfolio_id, instrument_id),
                ZERO,
            )
            if sold_quantity > available_quantity:
                report.add(
                    "AGGREGATE_SELL_EXCEEDS_HOLDING",
                    f"Combined sell quantity {sold_quantity} exceeds available "
                    f"quantity {available_quantity}.",
                    entity_type="proposal",
                    entity_id=proposal.proposal_id,
                )

    return report


from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from portfolio_rebalancer.rebalancer.proposals import (
    persist_rebalance_proposal,
)
from portfolio_rebalancer.rebalancer.trade_sizing import (
    RejectedTrade,
    TradeInstruction,
    TradeSizingResult,
)


class FakeSession:
    def __init__(self):
        self.added = []
        self.flush_called = False

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flush_called = True


def make_result():
    instructions = (
        TradeInstruction(
            portfolio_id="PORT-INV-000001-01",
            instrument_id="INS-000001",
            side="SELL",
            quantity=Decimal("2"),
            price=Decimal("100"),
            notional=Decimal("200"),
            estimated_fee=Decimal("2"),
            reason_codes=("OVERWEIGHT_ASSET_CLASS",),
        ),
        TradeInstruction(
            portfolio_id="PORT-INV-000001-01",
            instrument_id="INS-000002",
            side="BUY",
            quantity=Decimal("1"),
            price=Decimal("100"),
            notional=Decimal("100"),
            estimated_fee=Decimal("1"),
        ),
    )

    return TradeSizingResult(
        instructions=instructions,
        rejected=(
            RejectedTrade(
                portfolio_id="PORT-INV-000001-01",
                instrument_id="INS-000003",
                side="BUY",
                reason_codes=("MISSING_FEE_SCHEDULE",),
            ),
        ),
    )


def test_persists_proposal_and_trades_with_totals():
    session = FakeSession()

    proposal = persist_rebalance_proposal(
        session=session,
        proposal_id="RB-2026-000001",
        portfolio_id="PORT-INV-000001-01",
        as_of_date=date(2026, 10, 22),
        sizing_result=make_result(),
    )

    assert proposal.status == "DRAFT"
    assert proposal.estimated_turnover == Decimal("300")
    assert proposal.total_fees == Decimal("3")
    assert len(proposal.trades) == 2
    assert session.added == [proposal]
    assert session.flush_called


def test_trade_records_preserve_instruction_details():
    proposal = persist_rebalance_proposal(
        session=FakeSession(),
        proposal_id="RB-2026-000002",
        portfolio_id="PORT-INV-000001-01",
        as_of_date=date(2026, 10, 22),
        sizing_result=make_result(),
    )

    sell_trade = proposal.trades[0]

    assert sell_trade.trade_id == "TRD-RB-2026-000002-0001"
    assert sell_trade.side == "SELL"
    assert sell_trade.quantity == Decimal("2")
    assert sell_trade.price == Decimal("100")
    assert sell_trade.fees == Decimal("2")
    assert sell_trade.status == "PROPOSED"
    assert sell_trade.reason_codes == ["OVERWEIGHT_ASSET_CLASS"]


def test_rejected_candidates_are_not_saved_as_trades():
    proposal = persist_rebalance_proposal(
        session=FakeSession(),
        proposal_id="RB-2026-000003",
        portfolio_id="PORT-INV-000001-01",
        as_of_date=date(2026, 10, 22),
        sizing_result=make_result(),
    )

    assert all(
        trade.instrument_id != "INS-000003"
        for trade in proposal.trades
    )


def test_rejects_instruction_for_another_portfolio():
    result = TradeSizingResult(
        instructions=(
            TradeInstruction(
                portfolio_id="PORT-INV-999999-01",
                instrument_id="INS-000001",
                side="BUY",
                quantity=Decimal("1"),
                price=Decimal("100"),
                notional=Decimal("100"),
                estimated_fee=Decimal("1"),
            ),
        ),
        rejected=(),
    )

    with pytest.raises(ValueError, match="match portfolio_id"):
        persist_rebalance_proposal(
            session=FakeSession(),
            proposal_id="RB-2026-000004",
            portfolio_id="PORT-INV-000001-01",
            as_of_date=date(2026, 10, 22),
            sizing_result=result,
        )


from datetime import date
from decimal import Decimal

import pytest

from portfolio_rebalancer.rebalancer.decision_receipts import (
    build_decision_receipts,
    persist_decision_receipts,
)
from portfolio_rebalancer.rebalancer.trade_sizing import (
    RejectedTrade,
    TradeInstruction,
    TradeSizingResult,
)


AS_OF_DATE = date(2026, 10, 22)
PORTFOLIO_ID = "PORT-INV-000001-01"
PROPOSAL_ID = "RB-2026-000001"


class FakeSession:
    def __init__(self):
        self.added = []
        self.flush_called = False

    def add_all(self, objects):
        self.added.extend(objects)

    def flush(self):
        self.flush_called = True


def make_result():
    return TradeSizingResult(
        instructions=(
            TradeInstruction(
                portfolio_id=PORTFOLIO_ID,
                instrument_id="INS-000001",
                side="BUY",
                quantity=Decimal("2"),
                price=Decimal("100"),
                notional=Decimal("200"),
                estimated_fee=Decimal("1.00"),
            ),
        ),
        rejected=(
            RejectedTrade(
                portfolio_id=PORTFOLIO_ID,
                instrument_id="INS-000002",
                side="BUY",
                reason_codes=("MISSING_FEE_SCHEDULE",),
            ),
        ),
    )


def test_builds_receipts_for_accepted_and_rejected_decisions():
    receipts = build_decision_receipts(
        PROPOSAL_ID,
        PORTFOLIO_ID,
        AS_OF_DATE,
        make_result(),
    )

    assert len(receipts) == 2
    assert receipts[0]["status"] == "ACCEPTED"
    assert receipts[0]["notional"] == "200"
    assert receipts[0]["estimated_fee"] == "1.00"
    assert receipts[0]["policy_checks"][-1] == {
        "check": "TRADE_SIZING",
        "status": "PASS",
    }
    assert receipts[1]["status"] == "REJECTED"
    assert receipts[1]["reason_codes"] == ["MISSING_FEE_SCHEDULE"]
    assert receipts[1]["policy_checks"] == [
        {
            "check": "MISSING_FEE_SCHEDULE",
            "status": "FAIL",
        }
    ]


def test_receipt_ids_and_payloads_are_deterministic():
    first = build_decision_receipts(
        PROPOSAL_ID,
        PORTFOLIO_ID,
        AS_OF_DATE,
        make_result(),
    )
    second = build_decision_receipts(
        PROPOSAL_ID,
        PORTFOLIO_ID,
        AS_OF_DATE,
        make_result(),
    )

    assert first == second
    assert first[0]["receipt_id"] == "DR-RB-2026-000001-0001"
    assert first[1]["receipt_id"] == "DR-RB-2026-000001-0002"


def test_rejects_decision_for_another_portfolio():
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
        build_decision_receipts(
            PROPOSAL_ID,
            PORTFOLIO_ID,
            AS_OF_DATE,
            result,
        )


def test_persists_receipts_as_simulation_events():
    session = FakeSession()

    receipts = persist_decision_receipts(
        session,
        PROPOSAL_ID,
        PORTFOLIO_ID,
        AS_OF_DATE,
        make_result(),
    )

    assert len(receipts) == 2
    assert len(session.added) == 2
    assert session.flush_called
    assert all(
        event.event_type == "DECISION_RECEIPT"
        for event in session.added
    )
    assert all(
        event.correlation_id == PROPOSAL_ID
        for event in session.added
    )
    assert session.added[0].payload == receipts[0]

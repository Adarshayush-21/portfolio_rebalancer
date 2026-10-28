
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from portfolio_rebalancer.database.schema import SimulationEvent
from portfolio_rebalancer.rebalancer.trade_sizing import TradeSizingResult


def build_decision_receipts(
    proposal_id: str,
    portfolio_id: str,
    as_of_date: date,
    sizing_result: TradeSizingResult,
) -> list[dict]:
    if not proposal_id.strip():
        raise ValueError("proposal_id cannot be empty")

    if not portfolio_id.strip():
        raise ValueError("portfolio_id cannot be empty")

    if not isinstance(as_of_date, date):
        raise ValueError("as_of_date must be a date")

    receipts = []
    decisions = [
        ("ACCEPTED", instruction, ())
        for instruction in sizing_result.instructions
    ]
    decisions.extend(
        ("REJECTED", rejected, rejected.reason_codes)
        for rejected in sizing_result.rejected
    )

    for index, (status, decision, reason_codes) in enumerate(
        decisions,
        start=1,
    ):
        if decision.portfolio_id != portfolio_id:
            raise ValueError("All decisions must match portfolio_id")

        receipt = {
            "receipt_id": f"DR-{proposal_id}-{index:04d}",
            "proposal_id": proposal_id,
            "portfolio_id": portfolio_id,
            "as_of_date": as_of_date.isoformat(),
            "status": status,
            "instrument_id": decision.instrument_id,
            "side": decision.side,
            "reason_codes": list(reason_codes),
            "policy_checks": [
                {
                    "check": reason_code,
                    "status": "FAIL",
                }
                for reason_code in reason_codes
            ],
        }

        if status == "ACCEPTED":
            receipt.update(
                {
                    "quantity": str(decision.quantity),
                    "price": str(decision.price),
                    "notional": str(decision.notional),
                    "estimated_fee": str(decision.estimated_fee),
                }
            )
            receipt["policy_checks"].append(
                {
                    "check": "TRADE_SIZING",
                    "status": "PASS",
                }
            )

        receipts.append(receipt)

    return receipts


def persist_decision_receipts(
    session: Session,
    proposal_id: str,
    portfolio_id: str,
    as_of_date: date,
    sizing_result: TradeSizingResult,
) -> list[dict]:
    receipts = build_decision_receipts(
        proposal_id=proposal_id,
        portfolio_id=portfolio_id,
        as_of_date=as_of_date,
        sizing_result=sizing_result,
    )

    events = [
        SimulationEvent(
            event_id=receipt["receipt_id"],
            event_type="DECISION_RECEIPT",
            entity_type="TRADE_DECISION",
            entity_id=(
                receipt["instrument_id"]
                or receipt["receipt_id"]
            ),
            payload=receipt,
            correlation_id=proposal_id,
        )
        for receipt in receipts
    ]

    session.add_all(events)
    session.flush()

    return receipts

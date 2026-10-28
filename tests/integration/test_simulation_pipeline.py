from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from portfolio_rebalancer.database.schema import Base
from portfolio_rebalancer.models.events import SimulationEvent
from portfolio_rebalancer.models.fee_schedule import FeeSchedule
from portfolio_rebalancer.models.holding import Holding
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.investor import InvestorProfile
from portfolio_rebalancer.models.market_price import MarketPrice
from portfolio_rebalancer.models.portfolio import Portfolio
from portfolio_rebalancer.models.post_trade_position import PostTradePosition
from portfolio_rebalancer.models.rebalance_proposal import RebalanceProposal
from portfolio_rebalancer.models.target_allocation import TargetAllocation
from portfolio_rebalancer.models.trade import Trade
from portfolio_rebalancer.rebalancer.workflow import run_rebalancing
from portfolio_rebalancer.simulation.execution import simulate_proposal_execution

AS_OF_DATE = date(2026, 10, 22)
INVESTOR_ID = "INV-000001"
PORTFOLIO_ID = "PORT-INV-000001-01"
PROPOSAL_ID = "RB-2026-000001"
EQUITY_ID = "INS-000001"
BOND_ID = "INS-000002"


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add(
            InvestorProfile(
                investor_id=INVESTOR_ID,
                risk_profile="MODERATE",
                status="ACTIVE",
            )
        )
        db.flush()

        db.add(
            Portfolio(
                portfolio_id=PORTFOLIO_ID,
                investor_id=INVESTOR_ID,
                currency="INR",
                status="ACTIVE",
            )
        )

        db.add_all([
            Instrument(
                instrument_id=EQUITY_ID,
                symbol="TESTEQ",
                name="Test Equity",
                asset_class="EQUITY",
                currency="INR",
                status="ACTIVE",
            ),
            Instrument(
                instrument_id=BOND_ID,
                symbol="TESTBD",
                name="Test Bond",
                asset_class="BOND",
                currency="INR",
                status="ACTIVE",
            ),
        ])
        db.flush()

        db.add(
            Holding(
                holding_id=f"HOLD-{PORTFOLIO_ID}-{EQUITY_ID}",
                portfolio_id=PORTFOLIO_ID,
                instrument_id=EQUITY_ID,
                quantity=Decimal("10"),
                as_of_date=AS_OF_DATE,
            )
        )

        db.add_all([
            MarketPrice(
                price_id="PRICE-000001",
                instrument_id=EQUITY_ID,
                price_date=AS_OF_DATE,
                price=Decimal("100"),
                quality="VALID",
                source="SYNTHETIC",
            ),
            MarketPrice(
                price_id="PRICE-000002",
                instrument_id=BOND_ID,
                price_date=AS_OF_DATE,
                price=Decimal("50"),
                quality="VALID",
                source="SYNTHETIC",
            ),
        ])

        db.add_all([
            FeeSchedule(
                fee_schedule_id="FEE-000001",
                instrument_id=EQUITY_ID,
                asset_class="EQUITY",
                fee_rate=Decimal("0.001"),
                fixed_fee=Decimal("0"),
                minimum_fee=Decimal("0"),
                effective_from=AS_OF_DATE,
            ),
            FeeSchedule(
                fee_schedule_id="FEE-000002",
                instrument_id=BOND_ID,
                asset_class="BOND",
                fee_rate=Decimal("0.001"),
                fixed_fee=Decimal("0"),
                minimum_fee=Decimal("0"),
                effective_from=AS_OF_DATE,
            ),
        ])

        db.add_all([
            TargetAllocation(
                target_id="TARGET-000001",
                portfolio_id=PORTFOLIO_ID,
                asset_class="EQUITY",
                target_weight=Decimal("0.500000"),
                effective_from=AS_OF_DATE,
            ),
            TargetAllocation(
                target_id="TARGET-000002",
                portfolio_id=PORTFOLIO_ID,
                asset_class="BOND",
                target_weight=Decimal("0.500000"),
                effective_from=AS_OF_DATE,
            ),
        ])

        db.commit()
        yield db

    engine.dispose()


def test_rebalance_to_simulated_execution_pipeline(session):
    proposal_result = run_rebalancing(
        session=session,
        portfolio_id=PORTFOLIO_ID,
        as_of_date=AS_OF_DATE,
        proposal_id=PROPOSAL_ID,
    )

    assert proposal_result["status"] == "DRAFT"
    assert proposal_result["trade_count"] > 0
    assert proposal_result["receipt_count"] > 0

    proposal = session.get(RebalanceProposal, PROPOSAL_ID)
    assert proposal is not None
    assert proposal.status == "DRAFT"

    execution_result = simulate_proposal_execution(
        session=session,
        proposal_id=PROPOSAL_ID,
        execution_date=AS_OF_DATE,
    )
    session.commit()

    assert execution_result["status"] == "EXECUTED"
    assert execution_result["simulation_only"] is True
    assert execution_result["trade_count"] == proposal_result["trade_count"]

    proposal = session.get(RebalanceProposal, PROPOSAL_ID)
    assert proposal.status == "EXECUTED"

    trades = session.scalars(
        select(Trade).where(Trade.proposal_id == PROPOSAL_ID)
    ).all()
    assert len(trades) == proposal_result["trade_count"]
    assert all(trade.status == "EXECUTED" for trade in trades)

    positions = session.scalars(
        select(PostTradePosition).where(
            PostTradePosition.proposal_id == PROPOSAL_ID
        )
    ).all()
    assert positions
    assert all(position.quantity >= 0 for position in positions)

    events = session.scalars(
        select(SimulationEvent).where(
            SimulationEvent.correlation_id == PROPOSAL_ID
        )
    ).all()
    event_types = [event.event_type for event in events]

    assert event_types.count("SIMULATED_TRADE_EXECUTED") == len(trades)
    assert event_types.count("POST_TRADE_SNAPSHOT_CREATED") == 1
    assert event_types.count("SIMULATED_EXECUTION_COMPLETED") == 1

    snapshot = execution_result["post_trade_snapshot"]
    assert Decimal(str(snapshot["total_market_value"])) > 0
    assert Decimal(str(snapshot["total_fees"])) >= 0

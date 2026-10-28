
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from portfolio_rebalancer.database.schema import Base
from portfolio_rebalancer.models.events import SimulationEvent
from portfolio_rebalancer.models.holding import Holding
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.investor import InvestorProfile
from portfolio_rebalancer.models.market_price import MarketPrice
from portfolio_rebalancer.models.portfolio import Portfolio
from portfolio_rebalancer.models.post_trade_position import PostTradePosition
from portfolio_rebalancer.models.rebalance_proposal import RebalanceProposal
from portfolio_rebalancer.models.trade import Trade
from portfolio_rebalancer.simulation.execution import (
    simulate_proposal_execution,
)


AS_OF_DATE = date(2026, 10, 22)
INVESTOR_ID = "INV-000001"
PORTFOLIO_ID = "PORT-INV-000001-01"
PROPOSAL_ID = "RB-2026-000001"
EQUITY_ID = "INS-000001"
BOND_ID = "INS-000002"
EXCLUDED_ID = "INS-000003"


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

        db.add_all(
            [
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
                Instrument(
                    instrument_id=EXCLUDED_ID,
                    symbol="TESTEX",
                    name="Excluded Instrument",
                    asset_class="EQUITY",
                    currency="INR",
                    status="EXCLUDED",
                ),
            ]
        )
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

        db.add_all(
            [
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
                MarketPrice(
                    price_id="PRICE-000003",
                    instrument_id=EXCLUDED_ID,
                    price_date=AS_OF_DATE,
                    price=Decimal("25"),
                    quality="VALID",
                    source="SYNTHETIC",
                ),
            ]
        )

        db.add(
            RebalanceProposal(
                proposal_id=PROPOSAL_ID,
                portfolio_id=PORTFOLIO_ID,
                as_of_date=AS_OF_DATE,
                status="DRAFT",
                estimated_turnover=Decimal("100"),
                total_fees=Decimal("1"),
                rationale="Simulation test",
            )
        )
        db.commit()

        yield db

    engine.dispose()


def add_trade(
    session,
    instrument_id=BOND_ID,
    side="BUY",
    quantity=Decimal("2"),
    price=Decimal("50"),
):
    trade = Trade(
        trade_id=f"TRD-{PROPOSAL_ID}-0001",
        proposal_id=PROPOSAL_ID,
        instrument_id=instrument_id,
        side=side,
        quantity=quantity,
        price=price,
        fees=Decimal("1"),
        status="PROPOSED",
        reason_codes=["TEST"],
    )
    session.add(trade)
    session.commit()
    return trade


def test_successful_simulation_records_execution_and_snapshot(session):
    original_holding = session.get(
        Holding, f"HOLD-{PORTFOLIO_ID}-{EQUITY_ID}"
    )

    add_trade(session)

    result = simulate_proposal_execution(session, PROPOSAL_ID)

    session.commit()

    assert result["status"] == "EXECUTED"
    assert result["simulation_only"] is True
    assert result["trade_count"] == 1
    assert result["persisted_position_count"] == 2

    snapshot = result["post_trade_snapshot"]

    assert Decimal(snapshot["total_market_value"]) == Decimal("1100")
    assert Decimal(snapshot["estimated_turnover"]) == Decimal("100")
    assert Decimal(snapshot["total_fees"]) == Decimal("1")
    assert Decimal(snapshot["net_cash_flow_from_trades"]) == Decimal("-101")

    assert snapshot["post_trade_allocations"]["EQUITY"] == str(
        Decimal("1000") / Decimal("1100")
    )
    assert snapshot["post_trade_allocations"]["BOND"] == str(
        Decimal("100") / Decimal("1100")
    )

    assert original_holding.quantity == Decimal("10")
    assert session.get(RebalanceProposal, PROPOSAL_ID).status == "EXECUTED"

    trade = session.get(Trade, f"TRD-{PROPOSAL_ID}-0001")
    assert trade.status == "EXECUTED"

    positions = session.scalars(
        select(PostTradePosition).where(
            PostTradePosition.proposal_id == PROPOSAL_ID
        )
    ).all()

    assert len(positions) == 2

    positions_by_instrument = {
        position.instrument_id: position for position in positions
    }

    assert positions_by_instrument[EQUITY_ID].quantity == Decimal("10")
    assert positions_by_instrument[EQUITY_ID].valuation_price == Decimal("100")
    assert positions_by_instrument[EQUITY_ID].market_value == Decimal("1000")

    assert positions_by_instrument[BOND_ID].quantity == Decimal("2")
    assert positions_by_instrument[BOND_ID].valuation_price == Decimal("50")
    assert positions_by_instrument[BOND_ID].market_value == Decimal("100")
    assert positions_by_instrument[BOND_ID].valuation_date == AS_OF_DATE

    events = session.scalars(
        select(SimulationEvent).where(
            SimulationEvent.correlation_id == PROPOSAL_ID
        )
    ).all()

    assert len(events) == 3
    assert any(
        event.event_type == "POST_TRADE_SNAPSHOT_CREATED"
        for event in events
    )


def test_oversell_is_rejected_without_marking_trade_executed(session):
    add_trade(
        session,
        instrument_id=EQUITY_ID,
        side="SELL",
        quantity=Decimal("11"),
        price=Decimal("100"),
    )

    with pytest.raises(ValueError, match="negative"):
        simulate_proposal_execution(session, PROPOSAL_ID)

    session.expire_all()

    assert session.get(
        RebalanceProposal, PROPOSAL_ID
    ).status == "DRAFT"

    assert session.get(
        Trade, f"TRD-{PROPOSAL_ID}-0001"
    ).status == "PROPOSED"

    assert session.scalars(
        select(PostTradePosition).where(
            PostTradePosition.proposal_id == PROPOSAL_ID
        )
    ).all() == []


def test_excluded_instrument_buy_is_rejected(session):
    add_trade(
        session,
        instrument_id=EXCLUDED_ID,
        side="BUY",
        quantity=Decimal("1"),
        price=Decimal("25"),
    )

    with pytest.raises(ValueError, match="excluded"):
        simulate_proposal_execution(session, PROPOSAL_ID)

    assert session.scalars(
        select(PostTradePosition).where(
            PostTradePosition.proposal_id == PROPOSAL_ID
        )
    ).all() == []


def test_stale_price_is_not_silently_used(session):
    price = session.get(MarketPrice, "PRICE-000001")
    price.quality = "STALE"
    session.commit()

    add_trade(session)

    with pytest.raises(ValueError, match="STALE"):
        simulate_proposal_execution(session, PROPOSAL_ID)

    assert session.scalars(
        select(PostTradePosition).where(
            PostTradePosition.proposal_id == PROPOSAL_ID
        )
    ).all() == []


def test_duplicate_snapshot_is_rejected_without_overwriting(session):
    add_trade(session)

    first_result = simulate_proposal_execution(session, PROPOSAL_ID)
    session.commit()

    original_positions = session.scalars(
        select(PostTradePosition)
        .where(PostTradePosition.proposal_id == PROPOSAL_ID)
        .order_by(PostTradePosition.instrument_id)
    ).all()

    original_values = [
        (
            position.position_id,
            position.quantity,
            position.valuation_price,
            position.market_value,
        )
        for position in original_positions
    ]

    from portfolio_rebalancer.simulation.post_trade import (
        persist_post_trade_snapshot,
    )

    with pytest.raises(ValueError, match="already exist"):
        persist_post_trade_snapshot(session, first_result["post_trade_snapshot"])

    session.rollback()

    remaining_positions = session.scalars(
        select(PostTradePosition)
        .where(PostTradePosition.proposal_id == PROPOSAL_ID)
        .order_by(PostTradePosition.instrument_id)
    ).all()

    remaining_values = [
        (
            position.position_id,
            position.quantity,
            position.valuation_price,
            position.market_value,
        )
        for position in remaining_positions
    ]

    assert remaining_values == original_values
    assert len(remaining_positions) == 2


def test_execution_failure_can_be_fully_rolled_back(session, monkeypatch):
    from portfolio_rebalancer.simulation import execution

    add_trade(session)

    original_append = execution.append_simulation_event

    def fail_after_snapshot_event_is_written(**kwargs):
        event = original_append(**kwargs)

        if kwargs["event_type"] == "POST_TRADE_SNAPSHOT_CREATED":
            raise RuntimeError("Injected failure for rollback test")

        return event

    monkeypatch.setattr(
        execution,
        "append_simulation_event",
        fail_after_snapshot_event_is_written,
    )

    with pytest.raises(RuntimeError, match="Injected failure"):
        simulate_proposal_execution(session, PROPOSAL_ID)

    session.rollback()
    session.expire_all()

    assert session.get(
        RebalanceProposal, PROPOSAL_ID
    ).status == "DRAFT"

    assert session.get(
        Trade, f"TRD-{PROPOSAL_ID}-0001"
    ).status == "PROPOSED"

    positions = session.scalars(
        select(PostTradePosition).where(
            PostTradePosition.proposal_id == PROPOSAL_ID
        )
    ).all()
    assert positions == []

    events = session.scalars(
        select(SimulationEvent).where(
            SimulationEvent.correlation_id == PROPOSAL_ID
        )
    ).all()
    assert events == []


def test_simulation_rounds_trade_notional_to_cents(session):
    trade = add_trade(
        session,
        instrument_id=BOND_ID,
        side="BUY",
        quantity=Decimal("3"),
        price=Decimal("10.005"),
    )
    trade.fees = Decimal("0.50")
    session.commit()

    result = simulate_proposal_execution(session, PROPOSAL_ID)
    snapshot = result["post_trade_snapshot"]

    assert Decimal(snapshot["estimated_turnover"]) == Decimal("30.02")
    assert Decimal(snapshot["total_fees"]) == Decimal("0.50")
    assert Decimal(snapshot["net_cash_flow_from_trades"]) == Decimal("-30.52")

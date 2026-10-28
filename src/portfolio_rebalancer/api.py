from __future__ import annotations

import os
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from portfolio_rebalancer.calculations.allocations import (
    calculate_actual_allocations,
    get_active_target_allocations,
)
from portfolio_rebalancer.calculations.drift import calculate_allocation_drift
from portfolio_rebalancer.calculations.valuation import value_portfolio, total_market_value
from portfolio_rebalancer.database.connection import (
    create_database_engine,
    create_session_factory,
)
from portfolio_rebalancer.models.events import SimulationEvent
from portfolio_rebalancer.models.holding import Holding
from portfolio_rebalancer.models.instrument import Instrument
from portfolio_rebalancer.models.investor import InvestorProfile
from portfolio_rebalancer.models.portfolio import Portfolio
from portfolio_rebalancer.models.rebalance_proposal import RebalanceProposal
from portfolio_rebalancer.models.trade import Trade
from portfolio_rebalancer.rebalancer.workflow import run_rebalancing
from portfolio_rebalancer.simulation.execution import simulate_proposal_execution

DEFAULT_DATABASE = Path("outputs/final_run/portfolio_rebalancer.db")
DATABASE_PATH = Path(os.environ.get("PORTFOLIO_REBALANCER_DB", str(DEFAULT_DATABASE)))
engine = create_database_engine(DATABASE_PATH)
SessionFactory = create_session_factory(engine)

app = FastAPI(
    title="Portfolio Rebalancer API",
    description="Portfolio allocation analysis, policy-constrained proposals, and simulation-only execution.",
    version="1.0.0",
)

DASHBOARD_DIR = Path(__file__).parent / "dashboard"
app.mount("/dashboard-assets", StaticFiles(directory=str(DASHBOARD_DIR)), name="dashboard-assets")


class ProposalRequest(BaseModel):
    as_of_date: date | None = None
    drift_tolerance: Decimal = Field(default=Decimal("0.01"), ge=0, le=1)


def get_db():
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()


DBSession = Annotated[Session, Depends(get_db)]


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(DASHBOARD_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "database_path": str(DATABASE_PATH),
        "simulation_only": True,
    }


@app.get("/api/portfolios")
def list_portfolios(
    session: DBSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default="ACTIVE"),
):
    statement = (
        select(Portfolio, InvestorProfile.risk_profile)
        .join(InvestorProfile, Portfolio.investor_id == InvestorProfile.investor_id)
        .order_by(Portfolio.portfolio_id)
        .limit(limit)
        .offset(offset)
    )
    if status:
        statement = statement.where(Portfolio.status == status.upper())

    rows = session.execute(statement).all()
    total = session.scalar(
        select(func.count()).select_from(Portfolio).where(
            Portfolio.status == status.upper() if status else True
        )
    ) or 0

    return {
        "items": [
            {
                "portfolio_id": portfolio.portfolio_id,
                "investor_id": portfolio.investor_id,
                "risk_profile": risk_profile,
                "currency": portfolio.currency,
                "status": portfolio.status,
            }
            for portfolio, risk_profile in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _portfolio_analysis(session: Session, portfolio_id: str, as_of_date: date | None = None):
    portfolio = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail=f"Portfolio not found: {portfolio_id}")

    effective_date = as_of_date or session.scalar(
        select(func.max(Holding.as_of_date)).where(Holding.portfolio_id == portfolio_id)
    )
    if effective_date is None:
        raise HTTPException(status_code=404, detail=f"No holdings found for portfolio {portfolio_id}")

    try:
        valued = value_portfolio(session, portfolio_id, effective_date)
        actual = calculate_actual_allocations(valued)
        targets = get_active_target_allocations(session, portfolio_id, effective_date)
        drift = calculate_allocation_drift(actual, targets)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    total_value = total_market_value(valued)
    return portfolio, effective_date, valued, actual, targets, drift, total_value


@app.get("/api/portfolios/{portfolio_id}")
def portfolio_detail(portfolio_id: str, session: DBSession, as_of_date: date | None = None):
    portfolio, effective_date, valued, actual, targets, drift, total_value = _portfolio_analysis(
        session, portfolio_id, as_of_date
    )
    investor = session.get(InvestorProfile, portfolio.investor_id)
    holdings = sorted(valued, key=lambda item: item.market_value, reverse=True)
    return {
        "portfolio_id": portfolio.portfolio_id,
        "investor_id": portfolio.investor_id,
        "risk_profile": investor.risk_profile if investor else None,
        "status": portfolio.status,
        "currency": portfolio.currency,
        "as_of_date": effective_date.isoformat(),
        "total_market_value": str(total_value),
        "holding_count": len(valued),
        "actual_allocations": {key: str(value) for key, value in sorted(actual.items())},
        "target_allocations": {key: str(value) for key, value in sorted(targets.items())},
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
        "top_holdings": [
            {
                "instrument_id": item.instrument_id,
                "symbol": item.symbol,
                "asset_class": item.asset_class,
                "quantity": str(item.quantity),
                "price": str(item.price),
                "market_value": str(item.market_value),
                "price_date": item.price_date.isoformat(),
            }
            for item in holdings[:25]
        ],
    }


@app.get("/api/portfolios/{portfolio_id}/explanation")
def portfolio_explanation(portfolio_id: str, session: DBSession, as_of_date: date | None = None):
    portfolio, effective_date, valued, actual, targets, drift, total_value = _portfolio_analysis(
        session, portfolio_id, as_of_date
    )
    material = [item for item in drift if item.recommended_direction != "HOLD"]
    material.sort(key=lambda item: abs(item.drift), reverse=True)

    observations = []
    for item in material:
        observations.append({
            "asset_class": item.asset_class,
            "actual_weight": str(item.actual_weight),
            "target_weight": str(item.target_weight),
            "drift": str(item.drift),
            "direction": item.recommended_direction,
            "explanation": (
                f"{item.asset_class} is {abs(item.drift) * 100:.2f} percentage points "
                f"{'above' if item.drift > 0 else 'below'} its target. "
                f"The current allocation is {item.actual_weight * 100:.2f}% versus "
                f"a target of {item.target_weight * 100:.2f}%."
            ),
        })

    if not observations:
        summary = "All calculated asset-class allocations are within the configured 1 percentage-point drift tolerance."
    else:
        first = observations[0]
        summary = (
            f"The largest allocation deviation is {first['asset_class']} "
            f"({abs(Decimal(first['drift'])) * 100:.2f} percentage points "
            f"{'above' if Decimal(first['drift']) > 0 else 'below'} target). "
            f"Review the suggested {first['direction'].lower()} direction before proposing trades."
        )

    return {
        "portfolio_id": portfolio_id,
        "as_of_date": effective_date.isoformat(),
        "basis": "Deterministic explanation generated from calculated holdings, target weights, and allocation drift; not an external LLM output.",
        "summary": summary,
        "observations": observations,
        "total_market_value": str(total_value),
        "holding_count": len(valued),
    }


@app.post("/api/portfolios/{portfolio_id}/proposals")
def create_proposal(
    portfolio_id: str,
    request: ProposalRequest,
    session: DBSession,
):
    try:
        result = run_rebalancing(
            session=session,
            portfolio_id=portfolio_id,
            as_of_date=request.as_of_date,
            drift_tolerance=request.drift_tolerance,
        )
        session.commit()
        return result
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Database error while creating proposal.") from exc


@app.get("/api/proposals")
def list_proposals(
    session: DBSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    rows = session.scalars(
        select(RebalanceProposal)
        .order_by(RebalanceProposal.created_at.desc(), RebalanceProposal.proposal_id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "items": [
            {
                "proposal_id": item.proposal_id,
                "portfolio_id": item.portfolio_id,
                "as_of_date": item.as_of_date.isoformat(),
                "status": item.status,
                "estimated_turnover": str(item.estimated_turnover),
                "total_fees": str(item.total_fees),
                "rationale": item.rationale,
            }
            for item in rows
        ],
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/proposals/{proposal_id}")
def proposal_detail(proposal_id: str, session: DBSession):
    proposal = session.get(RebalanceProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {proposal_id}")
    trades = session.scalars(
        select(Trade).where(Trade.proposal_id == proposal_id).order_by(Trade.trade_id)
    ).all()
    return {
        "proposal_id": proposal.proposal_id,
        "portfolio_id": proposal.portfolio_id,
        "as_of_date": proposal.as_of_date.isoformat(),
        "status": proposal.status,
        "estimated_turnover": str(proposal.estimated_turnover),
        "total_fees": str(proposal.total_fees),
        "rationale": proposal.rationale,
        "trades": [
            {
                "trade_id": trade.trade_id,
                "instrument_id": trade.instrument_id,
                "side": trade.side,
                "quantity": str(trade.quantity),
                "price": str(trade.price),
                "fees": str(trade.fees),
                "status": trade.status,
                "reason_codes": trade.reason_codes,
            }
            for trade in trades
        ],
    }


@app.get("/api/proposals/{proposal_id}/receipts")
def proposal_receipts(proposal_id: str, session: DBSession):
    proposal = session.get(RebalanceProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {proposal_id}")
    events = session.scalars(
        select(SimulationEvent)
        .where(
            SimulationEvent.event_type == "DECISION_RECEIPT",
            SimulationEvent.correlation_id == proposal_id,
        )
        .order_by(SimulationEvent.event_id)
    ).all()
    return {
        "proposal_id": proposal_id,
        "count": len(events),
        "receipts": [event.payload for event in events],
    }


@app.post("/api/proposals/{proposal_id}/simulate")
def simulate_proposal(proposal_id: str, session: DBSession):
    try:
        result = simulate_proposal_execution(session, proposal_id)
        session.commit()
        return result
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Database error during simulation.") from exc

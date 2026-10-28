import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

from sqlalchemy import select

from portfolio_rebalancer.database.connection import (
    create_database_engine,
    create_session_factory,
)
from portfolio_rebalancer.models.events import SimulationEvent
from portfolio_rebalancer.models.post_trade_position import PostTradePosition
from portfolio_rebalancer.models.rebalance_proposal import RebalanceProposal
from portfolio_rebalancer.models.trade import Trade
from portfolio_rebalancer.simulation.execution import (
    simulate_proposal_execution,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Simulate execution of a rebalance proposal."
    )
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--proposal-id", required=True)
    parser.add_argument("--execution-date", type=date.fromisoformat)
    parser.add_argument("--stale-after-days", type=int, default=3)
    args = parser.parse_args()

    if not args.database.is_file():
        parser.error(f"Database does not exist: {args.database}")

    if args.stale_after_days < 0:
        parser.error("--stale-after-days cannot be negative")

    engine = create_database_engine(args.database)

    try:
        session_factory = create_session_factory(engine)

        with session_factory() as session:
            with session.begin():
                result = simulate_proposal_execution(
                    session=session,
                    proposal_id=args.proposal_id,
                    execution_date=args.execution_date,
                    stale_after_days=args.stale_after_days,
                )

                trades = session.scalars(
                    select(Trade).where(
                        Trade.proposal_id == args.proposal_id,
                        Trade.status == "EXECUTED",
                    )
                ).all()

                positions = session.scalars(
                    select(PostTradePosition).where(
                        PostTradePosition.proposal_id == args.proposal_id
                    )
                ).all()

                events = session.scalars(
                    select(SimulationEvent).where(
                        SimulationEvent.correlation_id == args.proposal_id
                    )
                ).all()

                proposal = session.get(
                    RebalanceProposal, args.proposal_id
                )

                summary = {
                    "database": str(args.database),
                    "proposal_id": args.proposal_id,
                    "status": proposal.status,
                    "simulation_only": result["simulation_only"],
                    "trade_count": len(trades),
                    "post_trade_position_count": len(positions),
                    "event_count": len(events),
                    "event_counts_by_type": dict(
                        sorted(
                            Counter(
                                event.event_type for event in events
                            ).items()
                        )
                    ),
                    "valuation_date": result["post_trade_snapshot"][
                        "valuation_date"
                    ],
                    "total_market_value": result["post_trade_snapshot"][
                        "total_market_value"
                    ],
                    "estimated_turnover": result["post_trade_snapshot"][
                        "estimated_turnover"
                    ],
                    "total_fees": result["post_trade_snapshot"][
                        "total_fees"
                    ],
                }

        print(json.dumps(summary, indent=2, default=str))
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

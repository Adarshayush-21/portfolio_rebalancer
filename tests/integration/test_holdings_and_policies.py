
from decimal import Decimal

from sqlalchemy import func, select

from portfolio_rebalancer.config import ProjectConfig
from portfolio_rebalancer.database.connection import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from portfolio_rebalancer.generator.master_data import generate_master_data
from portfolio_rebalancer.generator.market_data import generate_market_data
from portfolio_rebalancer.generator.holdings import generate_holdings_and_targets
from portfolio_rebalancer.generator.policies import generate_policies
from portfolio_rebalancer.models.constraint import Constraint
from portfolio_rebalancer.models.fee_schedule import FeeSchedule
from portfolio_rebalancer.models.holding import Holding
from portfolio_rebalancer.models.target_allocation import TargetAllocation


def test_holdings_targets_and_policies_are_generated(tmp_path):
    config = ProjectConfig(
        seed=20261022,
        portfolio_count=4,
        instrument_count=10,
        trading_days=10,
        start_date="2026-10-01",
        output_dir=tmp_path / "generated",
        ground_truth_dir=tmp_path / "ground_truth",
        database_path=tmp_path / "test.db",
    )

    engine = create_database_engine(config.database_path)
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        generate_master_data(session, config)
        session.commit()

        generate_market_data(session, config)
        session.commit()

        holding_counts = generate_holdings_and_targets(session, config)
        policy_counts = generate_policies(session, config)
        session.commit()

        assert holding_counts["holdings"] >= config.portfolio_count
        assert holding_counts["target_allocations"] >= config.portfolio_count
        assert policy_counts["fee_schedules"] == config.instrument_count
        assert policy_counts["constraints"] >= config.portfolio_count

        targets = session.scalars(select(TargetAllocation)).all()
        weights_by_portfolio = {}

        for target in targets:
            weights_by_portfolio[target.portfolio_id] = (
                weights_by_portfolio.get(target.portfolio_id, Decimal("0"))
                + target.target_weight
            )

        assert all(
            weight == Decimal("1.000000")
            for weight in weights_by_portfolio.values()
        )

        assert session.scalar(select(func.count()).select_from(Holding)) > 0
        assert session.scalar(select(func.count()).select_from(FeeSchedule)) == 10
        assert session.scalar(select(func.count()).select_from(Constraint)) >= 4

    engine.dispose()

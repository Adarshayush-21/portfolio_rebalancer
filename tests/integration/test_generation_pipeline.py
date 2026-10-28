
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from portfolio_rebalancer.config import ProjectConfig
from portfolio_rebalancer.database.connection import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from portfolio_rebalancer.generator.master_data import generate_master_data
from portfolio_rebalancer.generator.market_data import (
    generate_market_data,
    trading_dates,
)
from portfolio_rebalancer.models.market_price import MarketPrice


def test_trading_dates_returns_weekdays():
    dates = trading_dates("2026-10-01", 10)

    assert len(dates) == 10
    assert all(day.weekday() < 5 for day in dates)
    assert dates == sorted(dates)


def test_generators_create_expected_records(tmp_path):
    config = ProjectConfig(
        seed=20261022,
        portfolio_count=3,
        instrument_count=5,
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
        master_counts = generate_master_data(session, config)
        session.commit()

        assert master_counts == {
            "investors": 3,
            "portfolios": 3,
            "instruments": 5,
        }

        market_counts = generate_market_data(session, config, batch_size=7)
        session.commit()

        assert market_counts["instruments_priced"] == 5
        assert market_counts["trading_days"] == 10
        assert market_counts["market_price_rows"] == 50

        actual_count = session.scalar(
            select(func.count()).select_from(MarketPrice)
        )
        assert actual_count == 50

        invalid_prices = session.scalar(
            select(func.count())
            .select_from(MarketPrice)
            .where(MarketPrice.price <= Decimal("0"))
        )
        assert invalid_prices == 0

        price_dates = session.scalars(
            select(MarketPrice.price_date).distinct()
        ).all()
        assert len(price_dates) == 10
        assert min(price_dates) >= date.fromisoformat(config.start_date)

    engine.dispose()

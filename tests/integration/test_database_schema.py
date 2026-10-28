
from sqlalchemy import inspect

from portfolio_rebalancer.database.connection import (
    create_database_engine,
    initialize_database,
)


def test_database_contains_all_domain_tables(tmp_path):
    engine = create_database_engine(tmp_path / "test.db")

    initialize_database(engine)

    tables = set(inspect(engine).get_table_names())

    assert {
        "investor_profiles",
        "portfolios",
        "instruments",
        "holdings",
        "market_prices",
        "target_allocations",
        "fee_schedules",
        "constraints",
        "rebalance_proposals",
        "trades",
        "simulation_events",
        "anomaly_records",
    }.issubset(tables)

    engine.dispose()


def test_core_foreign_keys_are_defined(tmp_path):
    engine = create_database_engine(tmp_path / "test.db")

    initialize_database(engine)
    inspector = inspect(engine)

    assert inspector.get_foreign_keys("portfolios")[0]["referred_table"] == (
        "investor_profiles"
    )

    holding_forekeys = inspector.get_foreign_keys("holdings")
    holding_references = {
        foreign_key["referred_table"] for foreign_key in holding_forekeys
    }

    assert holding_references == {"portfolios", "instruments"}

    trade_forekeys = inspector.get_foreign_keys("trades")
    trade_references = {
        foreign_key["referred_table"] for foreign_key in trade_forekeys
    }

    assert trade_references == {"rebalance_proposals", "instruments"}

    engine.dispose()

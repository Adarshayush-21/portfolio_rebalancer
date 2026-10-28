
import pytest

from portfolio_rebalancer.generator.ids import (
    investor_id,
    portfolio_id,
    instrument_id,
    holding_id,
    rebalance_proposal_id,
)


def test_investor_id_format():
    assert investor_id(1) == "INV-000001"


def test_portfolio_id_format():
    assert portfolio_id(1) == "PORT-INV-000001-01"


def test_instrument_id_format():
    assert instrument_id(1) == "INS-000001"


def test_holding_id_format():
    assert holding_id("PORT-INV-000001-01", "INS-000001") == (
        "HOLD-PORT-INV-000001-01-INS-000001"
    )


def test_rebalance_proposal_id_format():
    assert rebalance_proposal_id(1) == "RB-2026-000001"


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_numbers_are_rejected(value):
    with pytest.raises(ValueError):
        investor_id(value)

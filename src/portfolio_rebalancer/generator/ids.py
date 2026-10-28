
def investor_id(number: int) -> str:
    _validate_number(number)
    return f"INV-{number:06d}"


def portfolio_id(investor_number: int, portfolio_number: int = 1) -> str:
    _validate_number(investor_number)
    _validate_number(portfolio_number)
    return f"PORT-{investor_id(investor_number)}-{portfolio_number:02d}"


def instrument_id(number: int) -> str:
    _validate_number(number)
    return f"INS-{number:06d}"


def holding_id(portfolio: str, instrument: str) -> str:
    if not portfolio.strip() or not instrument.strip():
        raise ValueError("Portfolio and instrument IDs cannot be empty")
    return f"HOLD-{portfolio}-{instrument}"


def rebalance_proposal_id(number: int, year: int = 2026) -> str:
    _validate_number(number)
    if not 1 <= year <= 9999:
        raise ValueError("year must be between 1 and 9999")
    return f"RB-{year}-{number:06d}"


def _validate_number(number: int) -> None:
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ValueError("number must be a positive integer")

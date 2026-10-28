# Business Rules

## Portfolio and holding rules

- Active portfolios require valid target allocations.
- Active target allocations must be valid for the applicable date and must not overlap.
- Active target weights are expected to total 100%.
- Holding quantities must not be negative.
- Holdings must not be dated after the validation date.
- Holdings require usable market prices for valuation.
- Stale market prices produce warnings rather than being silently treated as current.

## Instrument and fee rules

- Instruments use supported asset classes: `EQUITY`, `BOND`, `GOLD`, `CASH`, and `OTHER`.
- Active instruments require an applicable fee schedule.
- Fee schedules are date-effective.
- Trade fees are checked against the applicable fee schedule.

## Trade and policy rules

- Trades must reference valid proposals and instruments.
- A sell quantity must not exceed the available holding.
- A buy must not be recommended for an excluded instrument.
- Active constraints apply only within their effective date range and matching portfolio/instrument scope.
- `EXCLUDE_INSTRUMENT` prevents buys of the constrained instrument.
- `BLOCK_BUY` prevents buys; `BLOCK_SELL` prevents sells.
- `MAX_TRADE_VALUE` limits trade notional.
- `MIN_TRADE_VALUE` defines a minimum trade notional.
- Trade sides are `BUY` or `SELL`.

## Validation issue codes

The business validator includes the following issue codes where the corresponding condition is present:

- `NEGATIVE_HOLDING`
- `FUTURE_HOLDING`
- `MISSING_TARGET_ALLOCATION`
- `OVERLAPPING_TARGET_ALLOCATION`
- `UNUSABLE_MARKET_PRICE`
- `STALE_MARKET_PRICE`
- `MISSING_FEE_SCHEDULE`
- `TRADE_WITHOUT_PROPOSAL`
- `TRADE_WITHOUT_INSTRUMENT`
- `STALE_TRADE_PRICE`
- `BUY_EXCLUDED_INSTRUMENT`
- `TRADE_EXCEEDS_HOLDING`
- `BUY_CONSTRAINED_INSTRUMENT`
- `BUY_BLOCKED`
- `SELL_BLOCKED`
- `MAX_TRADE_VALUE_EXCEEDED`
- `MIN_TRADE_VALUE_VIOLATED`
- `FEE_MISMATCH`

`STALE_MARKET_PRICE` and `STALE_TRADE_PRICE` are warnings in the current implementation. Other severities are determined by the validation rule.

## Intentional anomaly testing

The generator can inject six known anomaly scenarios: target weights not totaling 100%, stale market price, missing fee schedule, sell exceeding holding, buy of an excluded instrument, and use of a historical trade price despite a newer valid price.

The ground-truth file identifies each injected anomaly and its expected detection code. A dataset with these intentional anomalies can correctly have a failed validation status.

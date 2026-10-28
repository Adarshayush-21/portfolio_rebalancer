# Sample Output

## Full-scale seeded generation

Configuration:

- Seed: `20261022`
- Portfolios: 1,000
- Investors: 1,000
- Instruments: 5,000
- Trading days: 250
- Start date: `2025-10-01`
- As-of date: `2026-09-15`

Observed generated record counts:

| Dataset | Count |
|---|---:|
| Investors | 1,000 |
| Portfolios | 1,000 |
| Instruments | 5,000 |
| Market-price rows | 1,250,000 |
| Holdings | 40,226 |
| Target allocations | 5,000 |
| Fee schedules after anomaly injection | 4,999 |
| Constraints | 1,051 |
| Ground-truth anomaly labels | 6 |

## Baseline validation

The baseline validation report passed with zero errors and zero warnings before the intentional anomaly findings were applied.

## Final seeded-anomaly validation

The final validation report contained four errors and two warnings. These corresponded to six intentional anomaly scenarios:

| Expected detection | Severity in observed report | Entity |
|---|---|---|
| `TARGET_WEIGHTS_NOT_100_PERCENT` | Error | `PORT-INV-000001-01` |
| `STALE_MARKET_PRICE` | Warning | `HOLD-PORT-INV-000008-01-INS-004048` |
| `MISSING_FEE_SCHEDULE` | Error | `INS-000001` |
| `TRADE_EXCEEDS_HOLDING` | Error | `TR-ANOM-000004` |
| `BUY_EXCLUDED_INSTRUMENT` | Error | `TR-ANOM-000005` |
| `STALE_TRADE_PRICE` | Warning | `TR-ANOM-000006` |

A failed final validation status is expected for this anomaly-injection run. The separate baseline report is the clean-data check.

## Simulated execution example

A previously verified clean simulation used portfolio `PORT-INV-000001-01` and proposal `RB-2025-000001`. It generated 25 trades and then simulated execution with 25 executed-trade records, 38 persisted post-trade positions, and 52 simulation events.

Execution was local and simulation-only; no real orders were submitted.

# Schema Overview

## Entity relationships

- `investor_profiles` 1-to-many `portfolios`
- `portfolios` 1-to-many `holdings`
- `instruments` 1-to-many `holdings`
- `instruments` 1-to-many `market_prices`
- `portfolios` 1-to-many `target_allocations`
- `portfolios` 1-to-many `rebalance_proposals`
- `rebalance_proposals` 1-to-many `trades`
- `instruments` 1-to-many `trades`
- `rebalance_proposals` 1-to-many `post_trade_positions`
- `instruments` 1-to-many `post_trade_positions`
- `portfolios` and `instruments` can scope `constraints`
- `fee_schedules` can be instrument-specific or asset-class-specific
- `simulation_events` reference an entity by `entity_type` and `entity_id`; the model stores these as indexed fields rather than ordinary foreign keys.
- `anomaly_records` identify the affected entity through `entity_type` and `entity_id`.

## Key integrity rules

- Primary keys uniquely identify persisted records.
- Holdings reference a portfolio and an instrument.
- Market prices reference an instrument.
- Target allocations reference a portfolio.
- Proposals reference a portfolio.
- Trades reference a proposal and an instrument.
- Constraints reference their optional portfolio and instrument scopes.
- Post-trade positions reference a proposal and instrument.

The model definitions use restrictive deletion behavior on several parent relationships so dependent records cannot be casually removed.

## Lifecycle

A rebalance proposal is created with an as-of date and status. Its trades record side, quantity, price, fees, status, and reason codes. Simulated execution updates trade/proposal lifecycle state, writes post-trade positions, and records simulation events.

## Source of truth

For exact column types, precision, nullability, indexes, unique constraints, check constraints, and foreign-key behavior, inspect the SQLAlchemy model files under `src/portfolio_rebalancer/models/` and database schema setup under `src/portfolio_rebalancer/database/`.

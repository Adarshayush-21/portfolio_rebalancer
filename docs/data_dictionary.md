# Data Dictionary

This document summarizes the principal persisted entities. The SQLAlchemy models in `src/portfolio_rebalancer/models/` are the source of truth for complete column definitions and constraints.

| Entity / table | Purpose | Key fields |
|---|---|---|
| `investor_profiles` | Investor identity and risk profile | `investor_id`, `risk_profile`, `status`, `created_at` |
| `portfolios` | Investor-owned portfolio | `portfolio_id`, `investor_id`, `currency`, `status` |
| `instruments` | Tradable or investable instruments | `instrument_id`, `symbol`, `name`, `asset_class`, `currency`, `status` |
| `holdings` | Dated instrument quantities in portfolios | `holding_id`, `portfolio_id`, `instrument_id`, `quantity`, `as_of_date` |
| `market_prices` | Dated prices and quality metadata | `price_id`, `instrument_id`, `price_date`, `price`, `quality`, `source` |
| `target_allocations` | Effective-dated portfolio targets | `target_id`, `portfolio_id`, `asset_class`, `target_weight`, `effective_from`, `effective_to` |
| `constraints` | Effective-dated portfolio/instrument policy constraints | `constraint_id`, `portfolio_id`, `instrument_id`, `constraint_type`, `parameters`, `effective_from`, `effective_to`, `status` |
| `fee_schedules` | Effective-dated instrument or asset-class fees | `fee_schedule_id`, `instrument_id`, `asset_class`, `fee_rate`, `fixed_fee`, `minimum_fee`, `effective_from`, `effective_to` |
| `rebalance_proposals` | Proposed or simulated portfolio rebalance | `proposal_id`, `portfolio_id`, `as_of_date`, `status`, `estimated_turnover`, `total_fees`, `rationale` |
| `trades` | Buy/sell decisions attached to proposals | `trade_id`, `proposal_id`, `instrument_id`, `side`, `quantity`, `price`, `fees`, `status`, `reason_codes` |
| `post_trade_positions` | Persisted simulated post-trade positions | `position_id`, `proposal_id`, `instrument_id`, `quantity`, `valuation_price`, `market_value`, `asset_class`, `valuation_date` |
| `simulation_events` | Append-style simulation event records | `event_id`, `event_type`, `entity_type`, `entity_id`, `occurred_at`, `payload`, `correlation_id` |
| `anomaly_records` | Anomaly tracking metadata | `anomaly_id`, `dataset_run_id`, `entity_type`, `entity_id`, `anomaly_type`, `severity`, `injected`, `detected`, `details` |

## Identifiers

The generator uses readable identifiers such as `INV-000001`, `PORT-INV-000001-01`, `INS-000001`, and holding IDs derived from portfolio and instrument IDs. Rebalance proposal IDs use the pattern `RB-YYYY-NNNNNN`.

## Important types

- Monetary values, quantities, weights, and fee rates use decimal/numeric representations where defined by the models.
- Dates determine applicable holdings, prices, targets, fees, and constraints.
- JSON fields store structured constraint parameters, trade reason codes, event payloads, and anomaly details.
- Foreign keys link dependent records to their parent entities. Consult the model definitions for exact nullability and deletion behavior.

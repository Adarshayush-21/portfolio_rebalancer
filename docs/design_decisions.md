# Design Decisions

## Reproducible synthetic data

Generation accepts an explicit seed. The challenge run uses seed `20261022` so the same configuration can be regenerated for verification. Exported artifacts and reproducibility utilities support comparison of generated results.

## Relational persistence

SQLAlchemy models represent parent entities and dependent records. Foreign keys and validation checks help expose orphaned or inconsistent records. SQLite provides a convenient local demonstration database.

## Decimal-based financial calculations

Financial quantities, prices, weights, and fees use decimal/numeric types in the domain models and calculation paths to reduce avoidable binary floating-point rounding errors.

## Effective-dated rules

Target allocations, fee schedules, and constraints include effective dates. The applicable rule must be evaluated relative to the relevant valuation or proposal date rather than assuming every record applies indefinitely.

## Validation before interpretation

The generation pipeline captures a baseline validation result and can then inject known anomalies. Final validation findings are compared with explicit ground-truth labels. Intentional anomaly findings are evidence that the validator detected seeded problems; they are not evidence of a clean dataset.

## Explicit decisions and lifecycle records

Rebalance proposals and trades are persisted as separate records. Decision receipts preserve reasons for trade decisions. Simulation events and post-trade positions make simulated execution inspectable after the workflow finishes.

## Simulation-only execution

The execution path updates the local simulation database. It is not a brokerage integration and does not submit real orders.

## Keep generated outputs separate from source

Large databases and exports are generated artifacts, not application source. The full-scale run is kept outside version control to avoid unnecessarily large repository history. The seed, scripts, configuration, documentation, and tests provide the reproducible workflow.

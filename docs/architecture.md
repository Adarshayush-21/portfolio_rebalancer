# Architecture

## Overview

Portfolio Rebalancer is a Python application for generating reproducible synthetic portfolio data, validating data and policy rules, proposing portfolio rebalances, and simulating trade execution.

## Main components

- `models/`: SQLAlchemy entities for investors, portfolios, instruments, holdings, prices, targets, constraints, fees, proposals, trades, events, and post-trade positions.
- `database/`: database base, connection, schema, repositories, and seeding.
- `generator/`: deterministic master-data, holdings, market-price, and policy generation; anomaly injection.
- `calculations/`: pricing, valuation, allocation, and drift calculations.
- `validation/`: integrity checks, business rules, reconciliation, and validation reports.
- `rebalancer/`: policy constraint evaluation, trade sizing, fee calculation, decision receipts, proposal creation, and workflow orchestration.
- `simulation/`: simulated execution, post-trade positions, and event logging.
- `evaluation/`: anomaly metrics, ground-truth handling, counterfactual evaluation, and reproducibility utilities.
- `reporting/`: CSV, JSON, SQL exports, manifests, and summaries.
- `scripts/`: command-line entry points for generation, validation, exporting, proposal creation, and simulation.

## Data flow

1. Generate synthetic master data and dependent records.
2. Validate baseline data before intentional anomaly injection.
3. Optionally inject known anomalies and record their ground-truth labels.
4. Validate the resulting dataset and export reports.
5. Calculate portfolio valuation, allocation drift, and proposed trades.
6. Record decision receipts and proposal/trade records.
7. Optionally simulate execution, persist post-trade positions, and append events.

## Persistence and safety

SQLAlchemy models use a relational database. The demonstrated workflow uses SQLite. Simulation updates local application records and does not submit real market orders.

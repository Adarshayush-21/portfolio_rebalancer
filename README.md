# Portfolio Rebalancer

A reproducible synthetic portfolio dataset generator and policy-constrained portfolio rebalancing workflow. The project models investors, portfolios, instruments, holdings, historical market prices, target allocations, trading policies, fees, constraints, and rebalance proposals.

## Features

- Deterministic synthetic data generation using a configurable random seed.
- Relational data model backed by SQLite.
- Portfolio valuation, allocation drift, and policy-constrained rebalance recommendations.
- Synthetic anomaly injection with separate ground-truth labels.
- Database integrity and business-rule validation.
- CSV and SQL exports, JSON reports, and reproducibility checks.
- Automated unit and integration tests.

## Requirements

- Python 3.13 or a compatible Python version supported by the project dependencies.
- Dependencies declared in `pyproject.toml`.
- PowerShell on Windows, or an equivalent terminal.

## Setup

From the project root, create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest
```

Run the test suite:

```powershell
python -m pytest -q
```

## Generate the dataset

The default scale is 1,000 portfolios, 5,000 instruments, and 250 trading days. The default seed is `20261022`.

Use dedicated paths for a full-scale run:

```powershell
python scripts\generate_data.py `
  --database outputs\full_run\portfolio_rebalancer.db `
  --output-dir outputs\full_run\generated `
  --ground-truth-dir outputs\full_run\ground_truth `
  --seed 20261022 `
  --portfolios 1000 `
  --instruments 5000 `
  --trading-days 250 `
  --start-date 2025-10-01
```

**Important:** Generation resets the database supplied through `--database`. Use a dedicated database path if you need to preserve existing data.

To generate a smaller dataset for development:

```powershell
python scripts\generate_data.py `
  --database outputs\dev\portfolio_rebalancer.db `
  --output-dir outputs\dev\generated `
  --ground-truth-dir outputs\dev\ground_truth `
  --portfolios 10 `
  --instruments 50 `
  --trading-days 20
```

To generate a clean baseline without injected anomalies, add `--no-anomalies`.

## Validate the dataset

Generation produces a summary and validation reports. Inspect:

- `outputs/full_run/generated/generation_summary.json`
- `outputs/full_run/generated/baseline_validation.json`
- `outputs/full_run/generated/validation_report.json`
- `outputs/full_run/ground_truth/ground_truth.json`

Run standalone validation using the generated summary's `as_of_date`:

```powershell
$summary = Get-Content outputs\full_run\generated\generation_summary.json -Raw | ConvertFrom-Json

python scripts\validate_data.py `
  --database outputs\full_run\portfolio_rebalancer.db `
  --as-of-date $summary.as_of_date `
  --output outputs\full_run\validation_report_standalone.json
```

The validator returns exit code `0` when the report passes and `1` when it does not. Review the report for errors and warnings rather than assuming that a successful generation means every business rule passed.

## Export data

Export database tables to CSV and create a SQL dump:

```powershell
python scripts\export_data.py `
  --database outputs\full_run\portfolio_rebalancer.db `
  --output-dir outputs\full_run\reexport
```

The generation pipeline also writes CSV exports and a SQL dump to its configured output directory.

## Run a rebalance proposal

The rebalancing CLI operates on an existing database. It does not generate the synthetic dataset.

```powershell
python -m portfolio_rebalancer.cli --help
```

Example:

```powershell
python -m portfolio_rebalancer.cli `
  --database outputs\full_run\portfolio_rebalancer.db `
  --portfolio-id PORT-INV-000001-01
```

Optional arguments include `--as-of-date`, `--proposal-id`, and `--drift-tolerance`. Use a portfolio identifier that exists in the selected database.

## Tests

Run all tests:

```powershell
python -m pytest -q
```

The suite covers unit-level behavior, generation, validation, anomaly detection, and reproducibility.

## Reproducibility

The default seed is `20261022`. With the same configuration and deterministic code, repeated generation should produce identical output files and row counts.

For repeatability checks, compare generated file hashes and row counts using the reproducibility utilities and tests.

## Project structure

```text
src/portfolio_rebalancer/
    calculations/    Valuation, allocations, and drift
    database/        Database setup, schema, and repositories
    evaluation/      Ground truth, metrics, reproducibility
    generator/       Synthetic data and anomaly generation
    models/          Domain entities
    rebalancer/      Trade sizing, constraints, fees, decisions
    reporting/       CSV, JSON, SQL, and summaries
    simulation/      Execution and post-trade simulation
    validation/      Integrity and business-rule checks

scripts/
    generate_data.py
    export_data.py
    validate_data.py
    run_rebalancing.py

tests/
docs/
data/
outputs/
```

## Data quality and interpretation

Synthetic ground-truth labels describe intentionally injected scenarios. Validation findings describe issues detected by the implemented rules. These are related but distinct: review detection metrics and the validation report to assess how well the rules identify the injected scenarios.

All generated records are simulated data and should not be interpreted as real investor accounts, market observations, or investment advice.

## API and Dashboard

The application includes a FastAPI backend and a browser-based dashboard for inspecting portfolios, reviewing allocation explanations, creating rebalance proposals, and examining simulation results and decision receipts.

### Install application dependencies

Install the project with the optional API and development dependencies:

```powershell
python -m pip install -e ".[app,dev]"
```

### Start the API

Start the API from the project root. The following example uses the generated full-scale database:

```powershell
$env:PORTFOLIO_REBALANCER_DB = "outputs\final_run\portfolio_rebalancer.db"

python -m uvicorn portfolio_rebalancer.api:app `
  --host 127.0.0.1 `
  --port 8000 `
  --workers 1
```

Ensure the database exists before starting the application. The `PORTFOLIO_REBALANCER_DB` environment variable can point to a different database.

Keep the terminal running while using the application.

### Open the application

With the API running, open these URLs in your browser:

- Dashboard: http://127.0.0.1:8000/
- Interactive API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

The dashboard uses the local API to load portfolio data and display explanations, proposals, and simulation information.

### API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check API health |
| GET | `/api/portfolios` | List portfolios |
| GET | `/api/portfolios/{portfolio_id}` | Retrieve portfolio details |
| GET | `/api/portfolios/{portfolio_id}/explanation` | Retrieve a portfolio explanation |
| POST | `/api/portfolios/{portfolio_id}/proposals` | Create a rebalance proposal |
| GET | `/api/proposals` | List proposals |
| GET | `/api/proposals/{proposal_id}` | Retrieve proposal details |
| GET | `/api/proposals/{proposal_id}/receipts` | Retrieve decision receipts |
| POST | `/api/proposals/{proposal_id}/simulate` | Simulate a proposal |

Use `/docs` to inspect request parameters, schemas, and responses.

### Simulation and safety

This project demonstrates simulated portfolio rebalancing. Proposal creation and simulation operate on the application's database and may change simulated records. They do not place orders with a broker or execute real-world trades.

Use a dedicated development database when testing workflows that modify proposal or simulation state. Do not point experiments at data you need to preserve.

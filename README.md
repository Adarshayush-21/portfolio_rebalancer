# Portfolio Rebalancer

A portfolio rebalancing and validation system developed for the YottaFlex AI Technologies Pvt. Ltd. **72 Hours Code Challenge**.

The project generates reproducible portfolio and market datasets, validates portfolio and trading data, detects anomalies, records detection results, and provides API and dashboard access.

## How to Run the Project

### 1. Install Dependencies

Python 3.11 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[app,dev]"
```

### 2. Run Tests

```powershell
python -m pytest -q
```

Expected result: all tests pass.

### 3. Generate the Dataset

```powershell
python scripts\generate_data.py `
  --database outputs\final_run\portfolio_rebalancer.db `
  --output-dir outputs\final_run\generated `
  --ground-truth-dir outputs\final_run\ground_truth `
  --seed 20261022 `
  --portfolios 1000 `
  --instruments 5000 `
  --trading-days 250 `
  --start-date 2025-10-01
```

**Note:** Dataset generation may take several minutes. It resets the database specified by `--database`, so do not use a database containing data you need to preserve.

### 4. Start the API Server

```powershell
$env:PORTFOLIO_REBALANCER_DB = "outputs\final_run\portfolio_rebalancer.db"

python -m uvicorn portfolio_rebalancer.api:app `
  --host 127.0.0.1 `
  --port 8000 `
  --workers 1
```

Keep the terminal running while using the application.

### 5. Open the Application

- **Dashboard:** http://127.0.0.1:8000/
- **API documentation:** http://127.0.0.1:8000/docs
- **Health check:** http://127.0.0.1:8000/api/health

## Features

- Reproducible portfolio and market-data generation.
- Portfolio and trading-data validation.
- Anomaly detection and ground-truth comparison.
- SQLite database persistence.
- CSV exports for generated data and detection results.
- REST API endpoints.
- Browser-based dashboard.
- Automated tests using pytest.

## Requirements

- Python 3.11 or newer.
- pip.
- Dependencies defined in `pyproject.toml`.

## Installation

If you have not already installed the project, create a virtual environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[app,dev]"
```

If the virtual environment is already active and dependencies are installed, you can skip this step.

## Data Generation

The `scripts/generate_data.py` script generates portfolio data, instruments, market prices, and ground-truth files.

Example configuration:

| Setting | Value |
|---|---|
| Random seed | `20261022` |
| Portfolios | `1000` |
| Instruments | `5000` |
| Trading days | `250` |
| Start date | `2025-10-01` |
| Database | `outputs/final_run/portfolio_rebalancer.db` |
| Generated CSV directory | `outputs/final_run/generated` |
| Ground-truth directory | `outputs/final_run/ground_truth` |

Using the same seed and configuration helps make dataset generation reproducible.

## Database and Output Files

The example run writes its output under `outputs/final_run/`.

| Path | Description |
|---|---|
| `outputs/final_run/portfolio_rebalancer.db` | SQLite database containing application data and anomaly records |
| `outputs/final_run/generated/` | Generated CSV files |
| `outputs/final_run/ground_truth/` | Ground-truth files for evaluating anomaly detection |

The API uses the database path configured by the `PORTFOLIO_REBALANCER_DB` environment variable.

## Validation

The project validates portfolio and trading data against configured business rules.

Potential findings include:

- Invalid or inconsistent target weights.
- Stale market prices.
- Missing fee schedules.
- Trades exceeding available holdings.
- Recommendations involving excluded instruments.
- Stale trade prices.

Validation results should be interpreted in the context of the dataset and its ground-truth labels. Deliberately injected negative cases may produce expected errors or warnings.

## Ground Truth and Anomaly Detection

Ground-truth files provide reference labels for evaluating anomaly detection.

The pipeline records anomaly information in the SQLite `AnomalyRecord` table and exports anomaly information to CSV where configured.

When evaluating a run, compare:

1. The number of anomalies injected.
2. The number of anomalies recorded.
3. Whether expected anomalies were marked as detected.
4. Whether database records and CSV exports agree.
5. Whether validation findings match the intended test cases.

Use the same seed and configuration when comparing runs.

## Running Tests

Run the test suite from the project root:

```powershell
python -m pytest -q
```

For detailed output:

```powershell
python -m pytest -v
```

The automated tests cover core project functionality, including data generation, validation, and anomaly recording.

## API and Dashboard

Start the API server with:

```powershell
$env:PORTFOLIO_REBALANCER_DB = "outputs\final_run\portfolio_rebalancer.db"

python -m uvicorn portfolio_rebalancer.api:app `
  --host 127.0.0.1 `
  --port 8000 `
  --workers 1
```

Available resources:

| Resource | URL | Description |
|---|---|---|
| Dashboard | http://127.0.0.1:8000/ | Browser-based application interface |
| API documentation | http://127.0.0.1:8000/docs | Interactive API documentation |
| Health check | http://127.0.0.1:8000/api/health | Application health endpoint |

Keep the API server running while using the dashboard or API.

## Project Structure

```text
portfolio-rebalancer/
├── portfolio_rebalancer/
├── scripts/
│   └── generate_data.py
├── outputs/
│   └── final_run/
│       ├── generated/
│       ├── ground_truth/
│       └── portfolio_rebalancer.db
├── tests/
├── README.md
└── pyproject.toml
```

Generated output directories and files may not exist until the data-generation command has been run.

## Data Quality and Interpretation

The dataset includes deliberately injected negative cases to exercise validation and anomaly detection.

Distinguish between:

- **Expected findings:** Issues intentionally introduced to test validation or detection.
- **Unexpected findings:** Issues not explained by the intended test cases or configuration.
- **Detection results:** Whether the pipeline identified and recorded an injected anomaly.
- **Validation results:** Whether data satisfies configured business rules.

A successful execution does not necessarily mean every validation result must be free of errors. Evaluate validation findings separately from anomaly-detection results.

## Troubleshooting

### Python or pip is not recognized

Check the installed versions:

```powershell
python --version
python -m pip --version
```

### Dependencies are missing

Activate the virtual environment and install dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[app,dev]"
```

### The API cannot find the database

Verify that the database exists and set the environment variable in the same PowerShell session used to start the server:

```powershell
$env:PORTFOLIO_REBALANCER_DB = "outputs\final_run\portfolio_rebalancer.db"
```

### The dashboard does not open

Confirm that the API server started successfully, then open:

http://127.0.0.1:8000/

### Tests fail

Run the tests with detailed output:

```powershell
python -m pytest -v
```

Review the first failure and its traceback before investigating subsequent failures.

## License

Refer to the repository's license information and challenge instructions for applicable usage and distribution terms.

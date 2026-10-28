# Portfolio Rebalancer — My Development History and AI Usage Disclosure

**Project:** Portfolio Rebalancer  
**Organization:** YottaFlex AI Technologies Pvt. Ltd.  
**Challenge:** 72-Hour Code Challenge  
**AI tool used:** ChatGPT  
**Record type:** Retrospective reconstruction of development activities  
**Prompt history status:** Original verbatim conversation history is not yet fully recovered

## 1. Project introduction

I developed Portfolio Rebalancer as an end-to-end portfolio management and rebalancing demonstration for the YottaFlex AI Technologies code challenge.

My objective was to build a working application that could generate synthetic financial data, validate its integrity, calculate portfolio allocations, identify deviations from target allocations, generate rebalancing proposals, enforce trading constraints, explain trade decisions, and simulate the resulting trades.

I approached the project as a connected system rather than a collection of unrelated scripts. The database, calculation engine, rebalancing logic, API, dashboard, and simulation needed to work together consistently.

Throughout development, I worked iteratively. I implemented and reviewed functionality, ran commands, inspected application responses, investigated calculation inconsistencies, added regression coverage, updated documentation, and checked the repository before submission.

I used ChatGPT as a supporting development tool for technical discussions, troubleshooting, reviewing calculations, exploring edge cases, improving tests, and refining documentation. I remained responsible for directing the work, integrating changes, reviewing the results, and preparing the submission.

## 2. Understanding the requirements and planning the architecture

I began by breaking the challenge into the major components needed for an end-to-end portfolio rebalancing workflow.

The main areas were:

- Domain modeling and relational database design.
- Synthetic financial data generation.
- Data integrity and business-rule validation.
- Portfolio valuation and allocation calculations.
- Rebalancing proposals and trading constraints.
- Decision receipts and rejection reasons.
- Backend API development.
- Browser-based dashboard integration.
- Trade simulation and post-trade reconciliation.
- Automated tests, documentation, and reproducibility checks.
- Data exports and submission preparation.

I considered how information would move through the system. Generated data needed to be stored in the database, calculations needed to use the appropriate portfolio and market information, proposals needed to reflect business rules, and the API needed to expose results that could be inspected through the dashboard.

I used ChatGPT to discuss implementation approaches and break down requirements into manageable technical tasks. I then worked through the implementation and used the available source code, tests, and application runs to review behavior.

## 3. Database and domain modeling

### 3.1 Relational data model

I worked on a relational data model using SQLite to represent the entities needed for the portfolio rebalancing workflow.

The documented domain includes:

- Investors.
- Portfolios.
- Financial instruments.
- Portfolio holdings.
- Historical market prices.
- Target allocations.
- Trading policies.
- Fee information.
- Rebalancing proposals.
- Trade decisions and decision receipts.

These entities are related. For example, a portfolio contains holdings, holdings refer to instruments, and valuation calculations depend on relevant prices. Rebalancing decisions also depend on target allocations and applicable policies.

I organized the database and domain-model code into the project's `src/portfolio_rebalancer/database/` and `src/portfolio_rebalancer/models/` areas.

### 3.2 Identifiers and data integrity

I considered how records would be identified and related so that generated data could be used consistently across calculations and validation.

The database needed to support relationships between parent records and dependent records. This influenced the order in which synthetic data could be generated and the checks needed to identify invalid references or inconsistent records.

I also worked with the distinction between database integrity and business-rule validation. A record may have valid references while still violating a business rule, so both types of checks are important.

### 3.3 Database isolation during testing

I used the `PORTFOLIO_REBALANCER_DB` environment variable to select the SQLite database used by the application.

During recorded API and simulation verification, I configured the application to use a temporary database. This was important because proposal simulation can change persisted simulated state.

Using a dedicated database allowed me to exercise the workflow without relying on data that needed to be preserved elsewhere.

The repository documentation also warns that data generation resets the database supplied to it. For that reason, separate paths should be used when testing generation, running the API, or preserving a particular dataset.

## 4. Synthetic financial data generation

### 4.1 Dataset requirements

I worked on the synthetic-data workflow so the application could be exercised without relying on private financial data or a live brokerage connection.

The documented default dataset scale is:

- 1,000 portfolios.
- 5,000 instruments.
- 250 trading days of historical prices.
- Default random seed: `20261022`.

The generator supports configurable inputs, dates, output paths, and anomaly-related behavior.

The implementation is organized under `src/portfolio_rebalancer/generator/`, with a command-line entry point at `scripts/generate_data.py`.

### 4.2 Generation dependencies

The data-generation workflow needs to create related entities in an appropriate order. Dependent records cannot be generated reliably before the records they reference exist.

I considered these dependencies while working on the generation workflow and its validation requirements.

I also considered how deterministic generation could make development and testing more repeatable. Using a fixed seed is useful, but reproducibility still needs to be checked against actual outputs and configuration.

### 4.3 Anomalies and ground truth

The project supports synthetic anomaly injection and ground-truth information.

I treated these as separate from validation findings:

- Ground truth identifies scenarios intentionally represented in the synthetic dataset.
- Validation findings represent issues detected by implemented checks.
- Evaluation compares detected findings with the intended scenarios.

This distinction matters because introducing an anomaly does not automatically prove that the validation system can detect it.

I used technical discussions and test planning to consider edge cases and the relationship between anomaly generation, validation, and evaluation.

### 4.4 Exports and reproducibility

The project includes CSV exports, SQL dumps, JSON reports, and reproducibility-related utilities and tests.

I worked on documenting how these outputs fit into the overall workflow and why fixed inputs, row counts, and file hashes can help verify repeatability.

The existence of reproducibility utilities does not establish that every full-scale repeat-generation and checksum comparison was completed. That still needs to be confirmed from the actual run outputs.

## 5. Data validation and business rules

I worked on the validation workflow to identify invalid or inconsistent data and enforce the requirements of the domain.

Validation is important at more than one stage. Generated data needs to be checked before it is used, and rebalancing decisions need to be checked against business rules before their results are treated as valid.

The project includes validation and evaluation code, along with scripts such as `scripts/validate_data.py`.

The main considerations included:

- Data integrity and relationships.
- Business-rule violations.
- Synthetic anomalies and their expected labels.
- Validation findings and reason codes.
- Consistency between calculations and stored results.

I used ChatGPT to reason through possible edge cases and improve the explanation of validation behavior. I reviewed the available code, tests, and outputs rather than assuming that the presence of a validation module proved every rule was covered.

## 6. Portfolio valuation and allocation calculations

I worked on the calculations needed to understand a portfolio's current state before proposing any rebalancing trades.

The calculation layer is organized under `src/portfolio_rebalancer/calculations/`.

The workflow uses portfolio holdings and relevant market prices to calculate portfolio values and allocation weights. These weights can then be compared with target allocations to identify drift.

The key relationship is that rebalancing decisions depend on the difference between the current portfolio state and the intended allocation.

I considered calculation consistency, edge cases, and the need for the resulting figures to remain consistent with later proposal and simulation stages.

Technical discussions and code review helped me examine calculation behavior and identify scenarios that deserved test coverage.

## 7. Rebalancing engine and trading constraints

### 7.1 Generating proposals

I worked on the rebalancing workflow that translates portfolio allocation drift into proposed trades.

The rebalancer is organized under `src/portfolio_rebalancer/rebalancer/`.

The proposal-generation process needs to account for portfolio state, target allocations, and applicable trading policies. A proposed trade should not automatically be treated as valid merely because it would move an allocation closer to its target.

### 7.2 Constraints and rejection reasons

The project models trading constraints, including maximum trade value and other applicable restrictions, as well as minimum trade requirements and fees.

I considered how the system should represent a trade that does not satisfy a policy. Rather than leaving the result unexplained, the workflow records decisions and reason codes.

The recorded API verification included a proposal named `RB-2026-000011`, which had 23 accepted receipts and one rejected receipt with the reason `MAX_TRADE_VALUE_EXCEEDED`.

This provided a concrete example of a rejected trade being represented explicitly in the decision workflow.

### 7.3 Decision receipts

I worked with the proposal and receipt workflow so accepted and rejected trade decisions could be inspected.

Decision receipts make the system more auditable by recording why a decision was made rather than presenting only a final list of trades.

I used technical discussions to examine policy behavior, rejection scenarios, and edge cases. The exact historical prompts for these activities are not available in the current record.

## 8. Backend development using FastAPI

### 8.1 API architecture

I worked on the FastAPI backend, implemented in `src/portfolio_rebalancer/api.py`.

The API provides access to portfolio data, explanations, proposals, decision receipts, and simulation workflows.

The documented endpoints are:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check application health |
| GET | `/api/portfolios` | List portfolios |
| GET | `/api/portfolios/{portfolio_id}` | Retrieve portfolio details |
| GET | `/api/portfolios/{portfolio_id}/explanation` | Retrieve a portfolio explanation |
| POST | `/api/portfolios/{portfolio_id}/proposals` | Create a rebalancing proposal |
| GET | `/api/proposals` | List proposals |
| GET | `/api/proposals/{proposal_id}` | Retrieve proposal details |
| GET | `/api/proposals/{proposal_id}/receipts` | Retrieve decision receipts |
| POST | `/api/proposals/{proposal_id}/simulate` | Simulate a proposal |

The interactive API documentation is available at `/docs` while the application is running.

### 8.2 Running and checking the API

I ran the API locally using Uvicorn and configured it to use a dedicated temporary SQLite database.

The recorded command pattern was:

```powershell
$snapshotRoot = Join-Path $env:TEMP "portfolio_rebalancer-clean-20261028-221332"
$testDb = Join-Path $env:TEMP "portfolio_rebalancer_test.db"

Set-Location $snapshotRoot
$env:PYTHONPATH = "$snapshotRoot\src"
$env:PORTFOLIO_REBALANCER_DB = $testDb

python -m uvicorn portfolio_rebalancer.api:app --host 127.0.0.1 --port 8001 --workers 1
```

I checked the health endpoint and inspected portfolio and proposal responses.

The recorded health response contained `status=ok` and `simulation_only=true`. A portfolio-list request with a limit of five returned five records and reported a total of 1,000.

These checks established that the application could start against the configured database and serve the inspected resources. They do not establish that every endpoint or failure condition was tested.

## 9. Frontend and dashboard

I worked with the browser-based dashboard as the user-facing interface for the portfolio rebalancing workflow.

The dashboard retrieves information from the backend rather than serving as the sole location for business rules and database access.

The intended workflow is:

1. Open the dashboard in a browser.
2. Request portfolio information from the FastAPI backend.
3. Retrieve data from the configured database through the backend.
4. Display portfolio details and explanations.
5. Create or inspect rebalancing proposals.
6. Review decision receipts and rejection reasons.
7. Inspect simulation results.

This division of responsibilities helps keep the backend responsible for data access and application logic while the frontend presents the returned information.

I used the local application workflow and API responses to inspect integration behavior and troubleshoot issues. The current historical record does not establish that every visual interaction or frontend edge case was tested, so I do not claim complete frontend verification.

## 10. Trade simulation

### 10.1 Simulation-only execution

I worked on the simulation workflow to evaluate proposal trades without placing live brokerage orders.

The simulation and post-trade code is organized under `src/portfolio_rebalancer/simulation/`.

The simulation processes accepted trades and produces results that can be inspected, including trade counts, persisted positions, fees, turnover, and allocation weights.

### 10.2 Recorded simulation run

During the recorded verification, proposal `RB-2026-000011` was simulated against a dedicated temporary database.

The recorded result reported:

- `simulation_only=true`
- `trade_count=23`
- `persisted_position_count=39`

The fee total matched the proposal's recorded total of 858.39, and post-trade allocation weights summed to 1.0.

These results provide evidence for the checks performed during that run. They do not prove that every possible portfolio configuration or market condition was tested.

## 11. Financial precision and reconciliation

One specific implementation issue involved consistency between proposal turnover, simulated turnover, and reconciliation.

Turnover calculations can disagree when different parts of the application use different rounding rules for trade notionals. I worked on aligning the relevant calculations so they use cent-rounded trade notionals.

The change was committed as:

`dbcf99d — Align simulated turnover with rounded trade notionals`

The simulation logic calculates rounded trade notionals before summing turnover and calculating the signed trade value. Reconciliation uses the same cent-rounding convention.

A regression test was added for a buy with:

- Quantity: 3.
- Price: 10.005.
- Fees: 0.50.

The test checks that the rounded turnover is 30.02 and the net cash flow is -30.52.

I reviewed the calculation change and the regression test result. The full test suite subsequently reported 45 passing tests.

This is a concrete example of identifying a consistency issue, changing the implementation, and adding a targeted test to protect the expected behavior.

## 12. Automated testing and debugging

I used pytest to run the automated tests while refining the project.

The tests are organized under `tests/` and cover several areas of the application, including calculations, generation, validation, anomaly detection, reproducibility, and simulation.

My workflow involved running the suite, examining errors or inconsistencies, changing the relevant implementation, and adding regression coverage where appropriate.

The recorded full test result after the simulation and reconciliation changes was:

**45 passed**

I used technical discussions to explore debugging approaches, identify possible edge cases, and improve test ideas. I relied on the actual test output and source changes as evidence of behavior.

A passing test suite establishes that the included tests passed. It does not prove that every acceptance criterion, full-scale generation scenario, API error condition, or frontend interaction has been tested.

## 13. Documentation and project organization

I worked on the README and supporting documentation to make the project easier to understand, run, and evaluate.

The repository contains documentation covering:

- Architecture.
- Business rules.
- Schema.
- Data dictionary.
- Design decisions.
- Sample output.

The README documents setup, data generation, validation, exports, API usage, tests, and simulation safety.

One concrete documentation correction aligned the README's Python minimum with the project configuration. The README was updated to state Python 3.11 or newer.

The change was committed as:

`7d6fe02 — Clarify Python requirement in README`

I also reviewed the documentation against the challenge requirements. Some aspects still need direct verification, particularly the completeness of generated artifacts, full-scale reproducibility evidence, and all field-level data dictionary requirements.

## 14. Git workflow and repository preparation

I used PowerShell and Git to manage the final project snapshot, review changes, commit updates, push them to the intended public repository, and verify synchronization.

The public repository is:

https://github.com/Adarshayush-21/portfolio_rebalancer

The recorded commits include:

- `dbcf99d` — Align simulated turnover with rounded trade notionals.
- `7d6fe02` — Clarify Python requirement in README.
- `5c46a12` — Document AI usage and reconstructed prompt history.

The final recorded push succeeded, and `git fetch origin` updated the remote-tracking branch to the same commit.

The final status showed:

```text
## main...origin/main
```

This indicated that the local `main` branch and `origin/main` were synchronized at that point.

I also expanded the AI disclosure so it clearly explains what the available history supports and what remains unavailable.

## 15. How I used AI during development

I used ChatGPT as a supporting tool for technical discussions and development tasks, including:

- Breaking down the challenge requirements.
- Exploring architecture and implementation approaches.
- Reasoning about database relationships and validation.
- Investigating calculation and trading-constraint behavior.
- Reviewing simulation and reconciliation consistency.
- Considering edge cases and regression tests.
- Troubleshooting local API and application workflows.
- Improving technical documentation.
- Working through PowerShell and Git commands.
- Preparing a checklist of remaining submission requirements.

I reviewed changes and used available tests, source inspection, application runs, and Git results to evaluate the work. I did not treat AI suggestions as a substitute for verification.

I take responsibility for understanding the project, the implementation that I submit, the checks I performed, and the limitations I disclose.

## 16. Verification summary

The available project and terminal records support the following statements:

- The application includes a SQLite-backed domain model and synthetic-data workflow.
- The project provides validation, rebalancing, API, dashboard, and simulation components.
- The API started successfully against a temporary database.
- The health endpoint and portfolio and proposal endpoints were inspected.
- A proposal's decision receipts included accepted trades and a rejected trade with an explicit reason.
- A proposal was simulated against a dedicated temporary database.
- Recorded simulation checks covered trade count, persisted positions, fees, and allocation weights.
- The turnover-rounding change included a targeted regression test.
- The full test suite reported 45 passing tests after the relevant changes.
- The README's Python requirement was aligned with the project configuration.
- The latest recorded Git status showed the local branch synchronized with the public repository.

The following items have not been conclusively established by the available record:

- Whether every challenge acceptance criterion has been satisfied.
- Whether all required generated artifacts are present and complete.
- Whether the required full-scale repeated-generation checksum comparison has been completed.
- Whether every required data dictionary field is documented.
- Whether every possible API, frontend, and business-rule edge case has been tested.

The project is a synthetic, simulation-only demonstration. It is not a production trading platform and does not place live broker orders.

## 17. Original prompt history

I requested a ChatGPT data export, and the confirmation stated that preparing the export may take a few days.

I did not preserve a complete separate prompt log during development. As a result, I cannot currently provide an exact chronological transcript of every original prompt and response.

This document reconstructs the main technical activities from the available project context and verification records. It does not claim that the task descriptions are the exact words I originally entered.

When the export becomes available, I will review the original conversations and supplement this record with recoverable prompts in chronological order. If any messages or conversations cannot be recovered, I will identify those gaps instead of inventing prompts or presenting reconstructed descriptions as original messages.

## 18. Final reflection

Building Portfolio Rebalancer involved connecting several components that needed to behave consistently: synthetic data, relational storage, financial calculations, trading policies, API responses, the dashboard, and post-trade simulation.

I approached the project iteratively, using implementation, testing, inspection, and documentation to improve the system. I paid particular attention to the consistency of financial calculations and the ability to inspect why trades were accepted or rejected.

I used AI as a supporting development tool while remaining responsible for the project direction, code review, verification, repository management, and final submission.

This record is intended to provide an honest explanation of my development process and the available verification evidence. It also identifies the areas where further evidence is needed. The original verbatim prompt history remains a separate outstanding item until I can recover the relevant conversations from the requested data export.

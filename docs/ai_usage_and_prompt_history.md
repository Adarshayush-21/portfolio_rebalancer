# AI Usage Disclosure and Prompt History

**Project:** Portfolio Rebalancer — YottaFlex AI Technologies Pvt. Ltd. 72-Hour Code Challenge
**AI tool used:** ChatGPT
**Record type:** Retrospective reconstruction from available conversation context
**Status:** Partial record; verbatim prompt history unavailable

## 1. Disclosure

ChatGPT was used as an AI-assisted development tool during this project to explore the solution design, work through implementation tasks, review code behavior, troubleshoot issues, improve tests and documentation, and prepare the submission.

I do not have a complete ChatGPT conversation export or a separately saved prompt log. This document is a retrospective summary of tasks reconstructed from available project context. It is not a verbatim transcript and must not be interpreted as a complete record of every prompt submitted.

ChatGPT is the only AI tool included in this record, based on my current recollection.

## 2. Reconstructed task history

These entries summarize the available development context. They are task summaries, not exact historical prompts.

### A. Solution design and architecture
- Explore an end-to-end portfolio rebalancing and policy-validation engine.
- Plan synthetic data generation, valuation, allocation drift, constrained trade sizing, fees, proposals, simulation, validation and exports.
- Consider decision receipts, reason codes, auditability, anomaly evaluation and reproducibility.

AI assistance: design exploration, requirement decomposition and implementation planning.

### B. Synthetic data and domain modeling
- Develop deterministic synthetic data and related entities.
- Organize master data before dependent records.
- Define identifiers, relationships, business rules, anomalies, ground-truth labels and validation checks.
- Document generation, schema, business rules and reproducibility.

AI assistance: implementation guidance, test ideas, code review and documentation.

### C. Rebalancing, constraints and simulation
- Review allocation and drift calculations.
- Work through trade sizing, excluded instruments, minimum trade sizes, fee schedules and policy violations.
- Generate proposals and decision receipts.
- Simulate accepted trades and calculate post-trade holdings, allocations, turnover and fees.

AI assistance: troubleshooting, business-rule reasoning, edge-case identification and calculation review.

### D. API and dashboard
- Run and inspect the FastAPI application.
- Exercise portfolio, proposal and receipt endpoints.
- Review dashboard workflows.
- Use a separate test database for state-changing simulation checks.

AI assistance: command-line guidance, debugging, API verification and UI troubleshooting.

### E. Testing and validation
- Run the test suite and investigate issues.
- Add a regression test for cent-rounded trade notionals.
- Review consistency between proposal turnover, simulated turnover and reconciliation.
- Verify simulation-only behavior.

AI assistance: test design, debugging and calculation consistency review.

Recorded result: the full test suite reported 45 passing tests after the simulation and reconciliation changes. This does not prove every possible scenario was tested.

### F. Documentation and submission preparation
- Review the README, project configuration and supporting documentation.
- Align the documented Python minimum with `pyproject.toml`.
- Verify Git status, commits, remote configuration and synchronization.
- Compare the project against challenge requirements and submission guidelines.

AI assistance: documentation review, Git guidance, compliance checklists and submission planning.

## 3. Checks reviewed or performed

Available terminal and project records support the following:
- Reviewed repository structure, README and Python project configuration.
- Ran the full test suite, which reported 45 passing tests after simulation and reconciliation changes.
- Checked API health and portfolio/proposal endpoints.
- Inspected accepted and rejected trade receipts.
- Executed a proposal in a dedicated test database and checked simulated positions, fees and allocations.
- Reviewed diffs and confirmed intended changes were committed.
- Verified pushes to the intended public GitHub repository and local/remote synchronization.
- Updated the README Python requirement to Python 3.11 or newer, matching project configuration.

These records do not establish that every requirement or possible behavior was verified.

## 4. AI contributions and limitations

ChatGPT provided implementation suggestions, debugging guidance, test ideas, code-review assistance and documentation support. Suggestions were not treated as proof of correctness; available tests, source inspection and application runs were used for validation.

This retrospective record does not establish the exact amount of code originally authored by AI versus written or modified manually. I do not claim all implementation details were independently authored or independently verified without supporting evidence.

## 5. Missing historical records

A complete verbatim prompt transcript was not preserved. Exact wording, timestamps and the complete sequence of original prompts are therefore unavailable.

I have not invented replacement prompts or represented reconstructed task summaries as exact historical messages. If an original conversation export or other historical record becomes available, it should supplement or replace the relevant reconstructed entries.

## 6. Verification boundaries

At the time this record was prepared:
- The recorded automated test result was 45 passing tests.
- The recorded simulation was simulation-only; no live broker orders were placed.
- The local Git branch was synchronized with the public repository.
- Full compliance with every challenge acceptance criterion had not been conclusively established.
- Dataset regeneration checksums, all required generated artifacts and all field-level data dictionary requirements still needed final confirmation.

## 7. Transparency commitment

This document is intended to explain where AI assisted the work, what was checked, and which historical details are unavailable. It should be updated if additional records become available or further validation changes the stated status.

# BugHunter AI

BugHunter AI is a portfolio-grade FastAPI application for detecting high-severity, production-critical bugs in recent repository changes. It focuses on issues that can cause crashes, authorization bypasses, data loss, leaked credentials, and resource exhaustion.

## Features

- Dark responsive frontend with analysis, dashboard, reports, memory, and settings pages
- FastAPI backend with GitHub URL simulation and ZIP upload ingestion
- Critical-only bug detection pipeline with confidence thresholds
- Persistent `MEMORIES.md` ledger to prevent duplicate reporting and duplicate PR creation
- PR lifecycle simulation with open PR tracking
- JSON report history plus an example markdown report
- Pytest coverage for detection and memory cleanup rules

## Project Structure

```text
bughunter-ai/
├── index.html
├── dashboard.html
├── analysis.html
├── report.html
├── memories.html
├── settings.html
├── css/
├── js/
├── backend/
├── templates/
├── static/
├── reports/
├── tests/
├── uploads/
├── sample-data/
├── MEMORIES.md
├── requirements.txt
├── app.py
└── README.md
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`.

## Usage

1. Enter a GitHub repository URL on `index.html` or `analysis.html`.
2. Run a scan to process recent simulated commits.
3. Review critical findings on `report.html`.
4. Create simulated PRs from report cards.
5. Inspect duplicate-prevention state on `memories.html`.

ZIP uploads are available from `analysis.html`. The backend extracts supported source files and runs the same critical-impact detectors.

## Detection Policy

BugHunter AI intentionally ignores low-priority issues. Reports are generated only for high-confidence critical patterns:

- Removed or weakened authorization checks
- Unbounded loops without cancellation or backoff
- Null reference crash paths from unsafe nested access
- Broad destructive operations
- Hard-coded credential-like values

When no critical issue is found, the scan returns:

```text
No critical bugs found.
```

## Memory Rules

`MEMORIES.md` tracks bug description, PR URL, status, and timestamp. The store:

- prevents duplicate active findings
- ignores bugs with open PRs
- removes merged entries
- keeps rejected entries for 30 days
- cleans stale memory entries automatically on read/write

## Tests

```bash
pytest
```

## Deployment Guide

For a simple VM or container deployment:

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

For production, place Uvicorn behind a reverse proxy, set durable storage for `reports/`, `uploads/`, and `MEMORIES.md`, and replace the simulated GitHub/PR adapters with GitHub App credentials.


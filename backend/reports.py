from __future__ import annotations

import json
from pathlib import Path

from .models import BugReport, ScanResult


def write_scan_report(scan: ScanResult, reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{scan.scan_id}.json"
    path.write_text(scan.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_scans(reports_dir: Path) -> list[ScanResult]:
    scans: list[ScanResult] = []
    if not reports_dir.exists():
        return scans
    for path in reports_dir.glob("*.json"):
        try:
            scans.append(ScanResult.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, ValueError):
            continue
    return sorted(scans, key=lambda scan: scan.completed_at, reverse=True)


def format_markdown(report: BugReport) -> str:
    return f"""# {report.title}

Severity: {report.severity}
Confidence: {report.confidence:.0%}

## Impact
{report.impact}

## Root Cause
{report.root_cause}

## Trigger Scenario
{report.trigger_scenario}

## Minimal Fix
{report.minimal_fix}

## Validation Steps
{chr(10).join(f"- {step}" for step in report.validation_steps)}
"""


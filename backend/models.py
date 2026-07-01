from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


class MemoryStatus(str, Enum):
    open = "open"
    pr_open = "pr_open"
    merged = "merged"
    rejected = "rejected"


class AnalysisRequest(BaseModel):
    repository_url: HttpUrl | None = None
    branch: str = "main"
    commit_limit: int = Field(default=8, ge=1, le=50)


class CommitChange(BaseModel):
    path: str
    diff: str
    language: str = "unknown"


class Commit(BaseModel):
    sha: str
    message: str
    author: str
    timestamp: datetime
    changes: list[CommitChange]


class BugReport(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    repository: str
    commit_sha: str
    title: str
    severity: str = "critical"
    confidence: float = Field(ge=0, le=1)
    impact: str
    root_cause: str
    trigger_scenario: str
    minimal_fix: str
    validation_steps: list[str]
    evidence: list[str] = Field(default_factory=list)
    status: MemoryStatus = MemoryStatus.open
    pr_url: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def fingerprint(self) -> str:
        return f"{self.repository}:{self.title}:{self.commit_sha[:12]}".lower()


class ScanResult(BaseModel):
    scan_id: str
    repository: str
    started_at: datetime
    completed_at: datetime
    commits_analyzed: int
    reports: list[BugReport]
    message: str


class MemoryEntry(BaseModel):
    fingerprint: str
    bug_description: str
    pr_url: str | None = None
    status: MemoryStatus = MemoryStatus.open
    timestamp: datetime


class DashboardStats(BaseModel):
    repositories_scanned: int
    critical_bugs_found: int
    open_prs: int
    resolved_bugs: int
    severity_distribution: dict[str, int]
    detection_history: list[dict[str, Any]]
    repository_scan_table: list[dict[str, Any]]


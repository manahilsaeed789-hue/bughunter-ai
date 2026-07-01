from datetime import datetime, timezone

from backend.analyzer import analyze_commits
from backend.models import Commit, CommitChange


def test_detects_permission_bypass():
    commit = Commit(
        sha="abc123",
        message="relax auth",
        author="tester",
        timestamp=datetime.now(timezone.utc),
        changes=[
            CommitChange(
                path="api/auth.py",
                language="python",
                diff='- if user and user.has_permission("admin"):\n+ if user:\n+     return sensitive_export()',
            )
        ],
    )

    reports = analyze_commits("demo", [commit], set())

    assert len(reports) == 1
    assert reports[0].severity == "critical"
    assert "Permission check bypass" in reports[0].title


def test_suppresses_known_active_bug():
    commit = Commit(
        sha="abc123",
        message="relax auth",
        author="tester",
        timestamp=datetime.now(timezone.utc),
        changes=[
            CommitChange(
                path="api/auth.py",
                language="python",
                diff='- if user and user.has_permission("admin"):\n+ if user:\n+     return sensitive_export()',
            )
        ],
    )
    first = analyze_commits("demo", [commit], set())
    second = analyze_commits("demo", [commit], {first[0].id})

    assert second == []


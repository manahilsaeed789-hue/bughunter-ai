from __future__ import annotations

import hashlib
import re

from .models import BugReport, Commit, CommitChange


def analyze_commits(repository: str, commits: list[Commit], active_fingerprints: set[str]) -> list[BugReport]:
    reports: list[BugReport] = []
    seen: set[str] = set(active_fingerprints)
    for commit in commits:
        for change in commit.changes:
            report = _detect(repository, commit, change)
            if not report:
                continue
            stable_fingerprint = _fingerprint(repository, report.title, change.path)[-12:]
            if stable_fingerprint in seen:
                continue
            report.id = stable_fingerprint
            seen.add(stable_fingerprint)
            reports.append(report)
    return reports


def _detect(repository: str, commit: Commit, change: CommitChange) -> BugReport | None:
    diff = change.diff
    checks = [
        _permission_bypass(repository, commit, change, diff),
        _infinite_loop(repository, commit, change, diff),
        _null_reference(repository, commit, change, diff),
        _destructive_delete(repository, commit, change, diff),
        _secret_leak(repository, commit, change, diff),
    ]
    high_confidence = [report for report in checks if report and report.confidence >= 0.82]
    return high_confidence[0] if high_confidence else None


def _permission_bypass(repository: str, commit: Commit, change: CommitChange, diff: str) -> BugReport | None:
    if re.search(r"-\s*.*has_permission|-\s*.*is_admin|-\s*.*role", diff) and re.search(r"\+\s*if\s+user\b", diff):
        return BugReport(
            repository=repository,
            commit_sha=commit.sha,
            title=f"Permission check bypass in {change.path}",
            confidence=0.94,
            impact="Privileged data or actions can be exposed to authenticated users without the required role.",
            root_cause="The change widens an authorization guard from a role/permission check to a simple user existence check.",
            trigger_scenario="A non-admin authenticated account calls the affected endpoint after the commit is deployed.",
            minimal_fix="Restore the explicit permission predicate and add a negative authorization test for ordinary users.",
            validation_steps=[
                "Run the endpoint test as an authenticated non-admin user.",
                "Confirm the request returns 403 and no sensitive payload is produced.",
            ],
            evidence=[change.path, "authorization guard removed from added diff"],
        )
    return None


def _infinite_loop(repository: str, commit: Commit, change: CommitChange, diff: str) -> BugReport | None:
    if "while True" in diff and not re.search(r"break|return|sleep|timeout|await", diff):
        return BugReport(
            repository=repository,
            commit_sha=commit.sha,
            title=f"Unbounded worker loop in {change.path}",
            confidence=0.9,
            impact="The worker can pin CPU or block shutdown, causing queue stalls and production resource exhaustion.",
            root_cause="A newly added infinite loop has no exit, backoff, cancellation, or timeout path.",
            trigger_scenario="Deploy the worker with an empty or blocked queue and attempt graceful shutdown or autoscaling.",
            minimal_fix="Add cancellation checks, bounded polling timeouts, and a backoff path when no work is available.",
            validation_steps=[
                "Start the worker with an empty queue.",
                "Send the process shutdown signal and verify it exits within the service deadline.",
            ],
            evidence=[change.path, "while True without a bounded termination path"],
        )
    return None


def _null_reference(repository: str, commit: Commit, change: CommitChange, diff: str) -> BugReport | None:
    chained_access = re.search(r"\+\s*.*\w+\.\w+\.\w+\.\w+", diff)
    optional_guard = re.search(r"if\s+.*\w+\.\w+|optional|try", diff, re.IGNORECASE)
    if chained_access and not optional_guard:
        return BugReport(
            repository=repository,
            commit_sha=commit.sha,
            title=f"Null reference crash path in {change.path}",
            confidence=0.86,
            impact="Malformed or partial input can crash the request path and return 500s to users.",
            root_cause="Nested object properties are dereferenced without validating that each parent object exists.",
            trigger_scenario="Submit a request body with the nested profile or address object omitted.",
            minimal_fix="Validate the input schema before dereferencing or use explicit optional checks with a 400 response.",
            validation_steps=[
                "Send a payload missing the nested object.",
                "Confirm the service returns a controlled validation error instead of an exception.",
            ],
            evidence=[change.path, chained_access.group(0).strip()],
        )
    return None


def _destructive_delete(repository: str, commit: Commit, change: CommitChange, diff: str) -> BugReport | None:
    if re.search(r"\+\s*.*(deleteMany|DROP TABLE|TRUNCATE|rm -rf)", diff, re.IGNORECASE):
        return BugReport(
            repository=repository,
            commit_sha=commit.sha,
            title=f"Potential data loss operation in {change.path}",
            confidence=0.88,
            impact="A broad destructive operation can erase production data beyond the intended scope.",
            root_cause="The change introduces a destructive command without an obvious tenant, user, or transaction boundary.",
            trigger_scenario="Run the path against a production-like database containing unrelated records.",
            minimal_fix="Require scoped predicates, dry-run logging, backups, and transaction rollback coverage.",
            validation_steps=["Execute against fixture data with multiple tenants.", "Verify only the intended records are removed."],
            evidence=[change.path, "broad destructive operation"],
        )
    return None


def _secret_leak(repository: str, commit: Commit, change: CommitChange, diff: str) -> BugReport | None:
    if re.search(r"\+\s*(API_KEY|SECRET|TOKEN|PASSWORD)\s*=\s*['\"][^'\"]{12,}", diff):
        return BugReport(
            repository=repository,
            commit_sha=commit.sha,
            title=f"Hard-coded credential in {change.path}",
            confidence=0.92,
            impact="A committed secret can grant unauthorized access to production systems or third-party services.",
            root_cause="A credential-like value was added directly to source instead of being read from secret storage.",
            trigger_scenario="The repository is cloned by an unauthorized actor or exposed through CI logs/artifacts.",
            minimal_fix="Revoke the credential, rotate dependent services, and load the value from a managed secret provider.",
            validation_steps=["Search history for the credential.", "Confirm the rotated secret is absent from source and CI output."],
            evidence=[change.path, "credential-like assignment"],
        )
    return None


def _fingerprint(repository: str, title: str, path: str) -> str:
    raw = f"{repository}:{title}:{path}".lower().encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

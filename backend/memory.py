from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import MemoryEntry, MemoryStatus

MEMORY_HEADER = """# BugHunter AI Memories

Persistent memory of high-confidence critical bugs and PR state.

| Fingerprint | Bug Description | PR URL | Status | Timestamp |
| --- | --- | --- | --- | --- |
"""


class MemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(MEMORY_HEADER, encoding="utf-8")

    def load(self) -> list[MemoryEntry]:
        rows: list[MemoryEntry] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| ") or line.startswith("| ---") or "Fingerprint" in line:
                continue
            parts = [part.strip() for part in line.strip("|").split("|")]
            if len(parts) != 5:
                continue
            fingerprint, description, pr_url, status, timestamp = parts
            try:
                rows.append(
                    MemoryEntry(
                        fingerprint=fingerprint,
                        bug_description=description,
                        pr_url=None if pr_url == "-" else pr_url,
                        status=MemoryStatus(status),
                        timestamp=datetime.fromisoformat(timestamp),
                    )
                )
            except ValueError:
                continue
        return self._clean(rows)

    def save(self, entries: list[MemoryEntry]) -> None:
        cleaned = self._clean(entries)
        lines = [MEMORY_HEADER.rstrip()]
        for entry in cleaned:
            lines.append(
                "| {fingerprint} | {description} | {pr_url} | {status} | {timestamp} |".format(
                    fingerprint=self._cell(entry.fingerprint),
                    description=self._cell(entry.bug_description),
                    pr_url=self._cell(entry.pr_url or "-"),
                    status=entry.status.value,
                    timestamp=entry.timestamp.isoformat(),
                )
            )
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def add_if_new(self, entry: MemoryEntry) -> bool:
        entries = self.load()
        existing = {item.fingerprint: item for item in entries}
        current = existing.get(entry.fingerprint)
        if current and current.status in {MemoryStatus.open, MemoryStatus.pr_open}:
            return False
        existing[entry.fingerprint] = entry
        self.save(list(existing.values()))
        return True

    def update_status(self, fingerprint: str, status: MemoryStatus, pr_url: str | None = None) -> MemoryEntry | None:
        entries = self.load()
        updated: MemoryEntry | None = None
        for entry in entries:
            if entry.fingerprint == fingerprint:
                entry.status = status
                if pr_url is not None:
                    entry.pr_url = pr_url
                entry.timestamp = datetime.now(timezone.utc)
                updated = entry
        self.save(entries)
        return updated

    def known_active_fingerprints(self) -> set[str]:
        return {
            item.fingerprint
            for item in self.load()
            if item.status in {MemoryStatus.open, MemoryStatus.pr_open}
        }

    def _clean(self, entries: list[MemoryEntry]) -> list[MemoryEntry]:
        now = datetime.now(timezone.utc)
        kept: list[MemoryEntry] = []
        for entry in entries:
            age = now - entry.timestamp
            if entry.status == MemoryStatus.merged:
                continue
            if entry.status == MemoryStatus.rejected and age > timedelta(days=30):
                continue
            kept.append(entry)
        return sorted(kept, key=lambda item: item.timestamp, reverse=True)

    @staticmethod
    def _cell(value: str) -> str:
        return re.sub(r"\s+", " ", value).replace("|", "/").strip()


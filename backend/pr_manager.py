from __future__ import annotations

from datetime import datetime, timezone

from .memory import MemoryStore
from .models import MemoryStatus


def create_pr(memory: MemoryStore, fingerprint: str, repository: str) -> dict[str, str]:
    entries = memory.load()
    entry = next((item for item in entries if item.fingerprint == fingerprint), None)
    if not entry:
        raise ValueError("Unknown bug fingerprint")
    if entry.status == MemoryStatus.pr_open and entry.pr_url:
        return {"status": "duplicate_prevented", "pr_url": entry.pr_url}

    pr_url = f"https://github.com/example/{repository}/pull/{abs(hash(fingerprint)) % 9000 + 1000}"
    memory.update_status(fingerprint, MemoryStatus.pr_open, pr_url=pr_url)
    return {"status": "created", "pr_url": pr_url, "created_at": datetime.now(timezone.utc).isoformat()}


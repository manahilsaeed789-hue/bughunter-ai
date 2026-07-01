from datetime import datetime, timedelta, timezone

from backend.memory import MemoryStore
from backend.models import MemoryEntry, MemoryStatus


def test_memory_cleans_merged_and_stale_rejected(tmp_path):
    store = MemoryStore(tmp_path / "MEMORIES.md")
    store.save(
        [
            MemoryEntry(
                fingerprint="merged",
                bug_description="merged bug",
                status=MemoryStatus.merged,
                timestamp=datetime.now(timezone.utc),
            ),
            MemoryEntry(
                fingerprint="stale",
                bug_description="old rejected bug",
                status=MemoryStatus.rejected,
                timestamp=datetime.now(timezone.utc) - timedelta(days=31),
            ),
            MemoryEntry(
                fingerprint="open",
                bug_description="open bug",
                status=MemoryStatus.open,
                timestamp=datetime.now(timezone.utc),
            ),
        ]
    )

    entries = store.load()

    assert [entry.fingerprint for entry in entries] == ["open"]


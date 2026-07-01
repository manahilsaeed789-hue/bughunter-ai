from __future__ import annotations

import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from .models import Commit, CommitChange

SAMPLE_DIFFS = [
    CommitChange(
        path="api/auth.py",
        language="python",
        diff="""@@
- if user and user.has_permission("admin"):
-     return sensitive_export()
+ if user:
+     return sensitive_export()
""",
    ),
    CommitChange(
        path="workers/billing.py",
        language="python",
        diff="""@@
+ while True:
+     invoice = queue.get()
+     charge_customer(invoice)
""",
    ),
    CommitChange(
        path="services/profile.js",
        language="javascript",
        diff="""@@
+ const city = request.body.profile.address.city.toLowerCase()
+ await db.users.update({ id: userId }, { city })
""",
    ),
]


def repository_name(repository_url: str | None, fallback: str = "uploaded-repository") -> str:
    if not repository_url:
        return fallback
    return repository_url.rstrip("/").split("/")[-1].replace(".git", "") or fallback


def load_recent_commits(repository_url: str | None, commit_limit: int) -> list[Commit]:
    repo = repository_name(repository_url)
    now = datetime.now(timezone.utc)
    commits: list[Commit] = []
    for index, change in enumerate(SAMPLE_DIFFS[:commit_limit]):
        commits.append(
            Commit(
                sha=uuid4().hex,
                message=f"Update {change.path} in {repo}",
                author="BugHunter sample feed",
                timestamp=now - timedelta(hours=index + 1),
                changes=[change],
            )
        )
    return commits


def load_zip_as_commits(zip_path: Path, commit_limit: int) -> list[Commit]:
    changes: list[CommitChange] = []
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if name.endswith("/") or len(changes) >= commit_limit:
                continue
            suffix = Path(name).suffix.lower()
            if suffix not in {".py", ".js", ".ts", ".tsx", ".java", ".go", ".rb"}:
                continue
            try:
                body = archive.read(name).decode("utf-8", errors="ignore")[:8000]
            except KeyError:
                continue
            changes.append(CommitChange(path=name, diff=body, language=suffix.lstrip(".")))

    if not changes:
        changes = SAMPLE_DIFFS[:1]

    return [
        Commit(
            sha=uuid4().hex,
            message=f"Analyze uploaded archive {zip_path.name}",
            author="ZIP upload",
            timestamp=datetime.now(timezone.utc),
            changes=changes,
        )
    ]


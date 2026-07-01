from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from backend.analyzer import analyze_commits
from backend.ingestion import load_recent_commits, load_zip_as_commits, repository_name
from backend.memory import MemoryStore
from backend.models import AnalysisRequest, DashboardStats, MemoryEntry
from backend.pr_manager import create_pr
from backend.reports import load_scans, write_scan_report

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"
MEMORY_PATH = BASE_DIR / "MEMORIES.md"

app = FastAPI(title="BugHunter AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/css", StaticFiles(directory=BASE_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=BASE_DIR / "js"), name="js")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

memory = MemoryStore(MEMORY_PATH)


@app.get("/")
def home() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/{page_name}.html")
def page(page_name: str) -> FileResponse:
    path = BASE_DIR / f"{page_name}.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(path)


@app.post("/api/analyze")
async def analyze(payload: AnalysisRequest) -> dict:
    commits = load_recent_commits(str(payload.repository_url) if payload.repository_url else None, payload.commit_limit)
    return _run_pipeline(repository_name(str(payload.repository_url) if payload.repository_url else None), commits)


@app.post("/api/analyze-upload")
async def analyze_upload(file: UploadFile = File(...), repository_name_form: str = Form("uploaded-repository")) -> dict:
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload a .zip archive")
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOADS_DIR / f"{uuid4().hex}_{Path(file.filename).name}"
    with target.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    commits = load_zip_as_commits(target, 20)
    return _run_pipeline(repository_name_form, commits)


@app.get("/api/dashboard", response_model=DashboardStats)
def dashboard() -> DashboardStats:
    scans = load_scans(REPORTS_DIR)
    repositories = {scan.repository for scan in scans}
    reports = [report for scan in scans for report in scan.reports]
    memories = memory.load()
    return DashboardStats(
        repositories_scanned=len(repositories),
        critical_bugs_found=len(reports),
        open_prs=sum(1 for item in memories if item.status.value == "pr_open"),
        resolved_bugs=sum(1 for report in reports if report.status.value == "merged"),
        severity_distribution={"critical": len(reports), "high": 0, "medium": 0},
        detection_history=[
            {"date": scan.completed_at.date().isoformat(), "bugs": len(scan.reports), "repository": scan.repository}
            for scan in reversed(scans[-10:])
        ],
        repository_scan_table=[
            {
                "scan_id": scan.scan_id,
                "repository": scan.repository,
                "completed_at": scan.completed_at.isoformat(),
                "commits": scan.commits_analyzed,
                "critical_bugs": len(scan.reports),
                "message": scan.message,
            }
            for scan in scans[:20]
        ],
    )


@app.get("/api/reports")
def reports() -> list[dict]:
    return [scan.model_dump(mode="json") for scan in load_scans(REPORTS_DIR)]


@app.get("/api/memories")
def memories() -> dict:
    return {"entries": [entry.model_dump(mode="json") for entry in memory.load()]}


@app.get("/api/memories.md", response_class=PlainTextResponse)
def memories_markdown() -> str:
    return MEMORY_PATH.read_text(encoding="utf-8")


@app.post("/api/pr/{fingerprint}")
def create_pull_request(fingerprint: str, repository: str = "repository") -> dict:
    try:
        return create_pr(memory, fingerprint, repository)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _run_pipeline(repository: str, commits: list) -> dict:
    started = datetime.now(timezone.utc)
    reports = analyze_commits(repository, commits, memory.known_active_fingerprints())
    for report in reports:
        memory.add_if_new(
            MemoryEntry(
                fingerprint=report.id,
                bug_description=report.title,
                pr_url=report.pr_url,
                status=report.status,
                timestamp=report.timestamp,
            )
        )
    completed = datetime.now(timezone.utc)
    scan = {
        "scan_id": uuid4().hex[:12],
        "repository": repository,
        "started_at": started,
        "completed_at": completed,
        "commits_analyzed": len(commits),
        "reports": reports,
        "message": "No critical bugs found." if not reports else f"{len(reports)} critical bug(s) found.",
    }
    from backend.models import ScanResult

    result = ScanResult.model_validate(scan)
    write_scan_report(result, REPORTS_DIR)
    return JSONResponse(content=result.model_dump(mode="json")).body and result.model_dump(mode="json")


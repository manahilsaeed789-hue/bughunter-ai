const API = {
  async get(path) {
    const response = await fetch(path);
    if (!response.ok) return demoGet(path);
    return response.json();
  },
  async post(path, body) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) return demoPost(path, body);
    return response.json();
  },
};

const DEMO_KEY = "bughunter_demo_scans";
const MEMORY_KEY = "bughunter_demo_memories";

function stored(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) || fallback;
  } catch {
    return fallback;
  }
}

function save(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function demoGet(path) {
  const scans = stored(DEMO_KEY, []);
  const memories = stored(MEMORY_KEY, []);
  if (path === "/api/reports") return scans;
  if (path === "/api/memories") return { entries: memories };
  if (path === "/api/dashboard") {
    const reports = scans.flatMap((scan) => scan.reports);
    return {
      repositories_scanned: new Set(scans.map((scan) => scan.repository)).size,
      critical_bugs_found: reports.length,
      open_prs: memories.filter((entry) => entry.status === "pr_open").length,
      resolved_bugs: 0,
      severity_distribution: { critical: reports.length, high: 0, medium: 0 },
      detection_history: scans.slice(-10).map((scan) => ({
        date: new Date(scan.completed_at).toISOString().slice(0, 10),
        bugs: scan.reports.length,
        repository: scan.repository,
      })),
      repository_scan_table: scans.slice().reverse().map((scan) => ({
        scan_id: scan.scan_id,
        repository: scan.repository,
        completed_at: scan.completed_at,
        commits: scan.commits_analyzed,
        critical_bugs: scan.reports.length,
        message: scan.message,
      })),
    };
  }
  throw new Error("Demo route not available");
}

function demoPost(path, body) {
  if (path.startsWith("/api/pr/")) {
    const fingerprint = path.split("/api/pr/")[1].split("?")[0];
    const memories = stored(MEMORY_KEY, []);
    const entry = memories.find((item) => item.fingerprint === fingerprint);
    if (entry?.pr_url) return { status: "duplicate_prevented", pr_url: entry.pr_url };
    const prUrl = `https://github.com/example/bughunter-ai/pull/${Math.floor(Math.random() * 8000) + 1000}`;
    if (entry) {
      entry.status = "pr_open";
      entry.pr_url = prUrl;
      entry.timestamp = new Date().toISOString();
      save(MEMORY_KEY, memories);
    }
    return { status: "created", pr_url: prUrl };
  }
  if (path === "/api/analyze") return createDemoScan(body?.repository_url || "demo-repository");
  throw new Error("Demo route not available");
}

function createDemoScan(repositoryUrl) {
  const repository = String(repositoryUrl).split("/").filter(Boolean).pop()?.replace(".git", "") || "demo-repository";
  const id = Math.random().toString(16).slice(2, 14);
  const report = {
    id,
    repository,
    commit_sha: Math.random().toString(16).slice(2, 14),
    title: "Permission check bypass in api/auth.py",
    severity: "critical",
    confidence: 0.94,
    impact: "Privileged data can be exposed to authenticated users without the required role.",
    root_cause: "The authorization guard was widened from a role check to a simple user existence check.",
    trigger_scenario: "A non-admin authenticated user calls the affected endpoint after deployment.",
    minimal_fix: "Restore the explicit permission predicate and add a negative authorization test.",
    validation_steps: ["Call the endpoint as a non-admin user.", "Confirm the response is 403."],
    evidence: ["api/auth.py", "authorization guard removed"],
    status: "open",
    pr_url: null,
    timestamp: new Date().toISOString(),
  };
  const scan = {
    scan_id: Math.random().toString(16).slice(2, 14),
    repository,
    started_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
    commits_analyzed: 3,
    reports: [report],
    message: "1 critical bug(s) found.",
  };
  const scans = stored(DEMO_KEY, []);
  const memories = stored(MEMORY_KEY, []);
  scans.push(scan);
  memories.unshift({
    fingerprint: id,
    bug_description: report.title,
    pr_url: null,
    status: "open",
    timestamp: report.timestamp,
  });
  save(DEMO_KEY, scans);
  save(MEMORY_KEY, memories);
  return scan;
}

function setActiveNav() {
  const current = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav-links a").forEach((link) => {
    if (link.getAttribute("href") === current) link.classList.add("active");
  });
}

function renderNav() {
  const nav = document.querySelector("[data-nav]");
  if (!nav) return;
  nav.innerHTML = `
    <div class="nav">
      <div class="shell nav-inner">
        <a class="brand" href="index.html">
          <span class="brand-mark">BH</span>
          <span>BugHunter AI</span>
        </a>
        <div class="nav-links">
          <a href="index.html">Analyze</a>
          <a href="dashboard.html">Dashboard</a>
          <a href="analysis.html">Pipeline</a>
          <a href="report.html">Reports</a>
          <a href="memories.html">Memories</a>
          <a href="settings.html">Settings</a>
        </div>
      </div>
    </div>`;
  setActiveNav();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

function reportCard(report) {
  return `
    <article class="card stack">
      <div class="report-title">
        <div>
          <span class="badge">${escapeHtml(report.severity)}</span>
          <h3 style="margin-top:10px">${escapeHtml(report.title)}</h3>
          <p>${escapeHtml(report.impact)}</p>
        </div>
        <strong>${Math.round(report.confidence * 100)}%</strong>
      </div>
      <div class="grid-2">
        <p><strong>Root cause</strong><br>${escapeHtml(report.root_cause)}</p>
        <p><strong>Trigger</strong><br>${escapeHtml(report.trigger_scenario)}</p>
      </div>
      <p><strong>Minimal fix</strong><br>${escapeHtml(report.minimal_fix)}</p>
      <button class="button secondary" data-pr="${escapeHtml(report.id)}" data-repo="${escapeHtml(report.repository)}">Create PR</button>
    </article>`;
}

async function loadDashboard() {
  const target = document.querySelector("[data-dashboard]");
  if (!target) return;
  const data = await API.get("/api/dashboard");
  target.innerHTML = `
    <div class="grid-4">
      <div class="card metric"><span>Repositories scanned</span><strong>${data.repositories_scanned}</strong></div>
      <div class="card metric"><span>Critical bugs found</span><strong>${data.critical_bugs_found}</strong></div>
      <div class="card metric"><span>Open PRs</span><strong>${data.open_prs}</strong></div>
      <div class="card metric"><span>Resolved bugs</span><strong>${data.resolved_bugs}</strong></div>
    </div>
    <div class="grid-2 section">
      <div class="panel"><h3>Severity Distribution</h3><canvas class="chart" id="severityChart"></canvas></div>
      <div class="panel"><h3>Detection History</h3><canvas class="chart" id="historyChart"></canvas></div>
    </div>
    <div class="panel">
      <h3>Repository Scan Table</h3>
      <table class="table">
        <thead><tr><th>Repository</th><th>Completed</th><th>Commits</th><th>Critical</th><th>Result</th></tr></thead>
        <tbody>${data.repository_scan_table.map((row) => `
          <tr><td>${escapeHtml(row.repository)}</td><td>${new Date(row.completed_at).toLocaleString()}</td><td>${row.commits}</td><td>${row.critical_bugs}</td><td>${escapeHtml(row.message)}</td></tr>`).join("") || `<tr><td colspan="5">No scans yet.</td></tr>`}
        </tbody>
      </table>
    </div>`;
  drawBars("severityChart", [data.severity_distribution.critical, data.severity_distribution.high, data.severity_distribution.medium], ["Critical", "High", "Medium"]);
  drawBars("historyChart", data.detection_history.map((item) => item.bugs), data.detection_history.map((item) => item.date));
}

function drawBars(id, values, labels) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width = canvas.clientWidth * devicePixelRatio;
  const height = canvas.height = canvas.clientHeight * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
  const max = Math.max(...values, 1);
  const gap = 16;
  const barWidth = (canvas.clientWidth - gap * (values.length + 1)) / Math.max(values.length, 1);
  ctx.clearRect(0, 0, width, height);
  values.forEach((value, index) => {
    const x = gap + index * (barWidth + gap);
    const barHeight = (canvas.clientHeight - 54) * (value / max);
    const y = canvas.clientHeight - barHeight - 28;
    ctx.fillStyle = index === 0 ? "#ef4444" : "#3b82f6";
    ctx.fillRect(x, y, barWidth, barHeight);
    ctx.fillStyle = "#94a3b8";
    ctx.font = "12px Inter, sans-serif";
    ctx.fillText(labels[index] || "", x, canvas.clientHeight - 8);
    ctx.fillStyle = "#e5e7eb";
    ctx.fillText(String(value), x, Math.max(16, y - 8));
  });
}

async function loadReports() {
  const target = document.querySelector("[data-reports]");
  if (!target) return;
  const scans = await API.get("/api/reports");
  const reports = scans.flatMap((scan) => scan.reports);
  target.innerHTML = reports.length ? reports.map(reportCard).join("") : `<div class="panel">No critical bugs found.</div>`;
}

async function loadMemories() {
  const target = document.querySelector("[data-memories]");
  if (!target) return;
  const data = await API.get("/api/memories");
  target.innerHTML = `
    <table class="table">
      <thead><tr><th>Bug</th><th>Status</th><th>PR</th><th>Timestamp</th></tr></thead>
      <tbody>${data.entries.map((entry) => `
        <tr>
          <td>${escapeHtml(entry.bug_description)}</td>
          <td><span class="badge">${escapeHtml(entry.status)}</span></td>
          <td>${entry.pr_url ? `<a href="${escapeHtml(entry.pr_url)}">${escapeHtml(entry.pr_url)}</a>` : "-"}</td>
          <td>${new Date(entry.timestamp).toLocaleString()}</td>
        </tr>`).join("") || `<tr><td colspan="4">No memories yet.</td></tr>`}
      </tbody>
    </table>`;
}

function bindAnalysisForm() {
  const form = document.querySelector("[data-analysis-form]");
  if (!form) return;
  const output = document.querySelector("[data-output]");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    output.textContent = "Loading commits...\nParsing diffs...\nRunning critical-impact detectors...";
    try {
      const result = await API.post("/api/analyze", {
        repository_url: formData.get("repository_url") || null,
        branch: formData.get("branch") || "main",
        commit_limit: Number(formData.get("commit_limit") || 8),
      });
      output.textContent = JSON.stringify(result, null, 2);
    } catch (error) {
      output.textContent = error.message;
    }
  });
}

function bindUploadForm() {
  const form = document.querySelector("[data-upload-form]");
  if (!form) return;
  const output = document.querySelector("[data-output]");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch("/api/analyze-upload", {
        method: "POST",
        body: new FormData(form),
      });
      output.textContent = response.ok
        ? JSON.stringify(await response.json(), null, 2)
        : JSON.stringify(createDemoScan("uploaded-repository"), null, 2);
    } catch {
      output.textContent = JSON.stringify(createDemoScan("uploaded-repository"), null, 2);
    }
  });
}

function bindPrButtons() {
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-pr]");
    if (!button) return;
    button.disabled = true;
    button.textContent = "Creating...";
    try {
      const repo = encodeURIComponent(button.dataset.repo || "repository");
      const result = await API.post(`/api/pr/${button.dataset.pr}?repository=${repo}`, {});
      button.textContent = result.status === "duplicate_prevented" ? "PR already open" : "PR created";
    } catch {
      button.textContent = "Unable to create PR";
    }
  });
}

renderNav();
bindAnalysisForm();
bindUploadForm();
bindPrButtons();
loadDashboard().catch(console.error);
loadReports().catch(console.error);
loadMemories().catch(console.error);

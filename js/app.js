const API = {
  async get(path) {
    const response = await fetch(path);
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  },
  async post(path, body) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  },
};

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
    const response = await fetch("/api/analyze-upload", {
      method: "POST",
      body: new FormData(form),
    });
    output.textContent = response.ok ? JSON.stringify(await response.json(), null, 2) : await response.text();
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

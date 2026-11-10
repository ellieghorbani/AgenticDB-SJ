"""Self-contained portfolio demonstration page."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["demo"])


_DEMO_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>AgenticDB-SJ Demo</title>
  <style>
    :root {
      --bg: #f5f7fb;
      --panel: #ffffff;
      --ink: #142033;
      --muted: #607089;
      --line: #dce3ee;
      --accent: #2563eb;
      --accent-dark: #1748b5;
      --good: #087f5b;
      --warn: #b45309;
      --bad: #b42318;
      --code: #0f172a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 15px/1.5 Inter, ui-sans-serif, system-ui, -apple-system,
            BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }
    header {
      padding: 28px max(24px, calc((100% - 1180px) / 2));
      background: linear-gradient(120deg, #0f2a5f, #2359c7);
      color: white;
    }
    header h1 { margin: 0 0 6px; font-size: 31px; }
    header p { margin: 0; max-width: 820px; opacity: .9; }
    main {
      max-width: 1180px;
      margin: 24px auto 56px;
      padding: 0 20px;
      display: grid;
      gap: 18px;
    }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 20px;
      box-shadow: 0 8px 28px rgba(20,32,51,.06);
    }
    h2 { margin: 0 0 14px; font-size: 19px; }
    h3 { margin: 18px 0 8px; font-size: 15px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    textarea, select, input {
      width: 100%;
      border: 1px solid #cbd5e1;
      border-radius: 9px;
      padding: 10px 12px;
      background: white;
      color: var(--ink);
      font: inherit;
    }
    textarea { min-height: 105px; resize: vertical; }
    button {
      border: 0;
      border-radius: 9px;
      padding: 10px 15px;
      font-weight: 700;
      cursor: pointer;
      background: var(--accent);
      color: white;
    }
    button:hover { background: var(--accent-dark); }
    button.secondary { background: #e8eef9; color: #1e3a67; }
    .actions { display: flex; gap: 9px; margin-top: 14px; flex-wrap: wrap; }
    .status-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0,1fr));
      gap: 10px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
      min-height: 86px;
    }
    .card strong { display:block; font-size: 12px; color: var(--muted); }
    .card span { display:block; margin-top: 8px; font-weight: 750; }
    .good { color: var(--good); }
    .warn { color: var(--warn); }
    .bad { color: var(--bad); }
    .answer {
      padding: 14px;
      border-radius: 10px;
      background: #eef5ff;
      border-left: 4px solid var(--accent);
      min-height: 64px;
    }
    .evidence { display: grid; gap: 8px; }
    .evidence article {
      border: 1px solid var(--line);
      border-radius: 9px;
      padding: 10px;
      overflow-wrap: anywhere;
    }
    details { margin-top: 12px; }
    pre {
      overflow: auto;
      max-height: 470px;
      background: var(--code);
      color: #dbeafe;
      border-radius: 10px;
      padding: 14px;
      font: 12px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
      white-space: pre-wrap;
    }
    .samples { display:flex; gap:8px; flex-wrap:wrap; }
    .samples button {
      font-size: 12px;
      padding: 7px 10px;
      background: #edf2fb;
      color: #294a7a;
    }
    .muted { color: var(--muted); }
    @media (max-width: 820px) {
      .grid, .status-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<header>
  <h1>AgenticDB-SJ</h1>
  <p>
    Natural-language querying over real relational, geospatial, and vector data
    with OpenAI structured planning, deterministic SQL templates, SQLGlot AST
    validation, restricted read-only execution, and evidence-backed answers.
  </p>
</header>

<main>
  <section class="panel">
    <div class="status-grid" id="statusCards">
      <div class="card"><strong>API</strong><span>Checking…</span></div>
      <div class="card"><strong>Database</strong><span>Checking…</span></div>
      <div class="card"><strong>AI provider</strong><span>Checking…</span></div>
      <div class="card"><strong>Release</strong><span>Checking…</span></div>
    </div>
  </section>

  <section class="grid">
    <div class="panel">
      <h2>Run the copilot</h2>
      <label for="mode">Workflow</label>
      <select id="mode">
        <option value="llm">OpenAI-assisted SQL workflow</option>
        <option value="deterministic">Deterministic SQL workflow</option>
        <option value="vector">Semantic / hybrid vector search</option>
      </select>

      <label for="provider">Planning provider</label>
      <select id="provider">
        <option value="openai">OpenAI</option>
        <option value="deterministic">Deterministic fallback</option>
      </select>

      <label for="question">Question</label>
      <textarea id="question">Which neighborhoods contain at least three active schools and two open park features?</textarea>

      <div class="samples">
        <button type="button" data-q="Which neighborhoods contain at least three active schools and two open park features?" data-mode="llm">SQL + spatial</button>
        <button type="button" data-q="Find open park features related to community centers and libraries." data-mode="vector">Vector search</button>
        <button type="button" data-q="Which elementary schools are within one mile of an open park?" data-mode="llm">Distance query</button>
      </div>

      <label for="evidence">Evidence rows</label>
      <input id="evidence" type="number" min="0" max="20" value="5">

      <div class="actions">
        <button id="runButton" type="button">Run query</button>
        <button id="refreshButton" class="secondary" type="button">Refresh status</button>
      </div>
      <p id="requestState" class="muted"></p>
    </div>

    <div class="panel">
      <h2>Answer</h2>
      <div id="answer" class="answer">Run a question to see an answer.</div>
      <h3>Evidence</h3>
      <div id="evidenceRows" class="evidence muted">No evidence yet.</div>
      <details>
        <summary>Tool trace</summary>
        <pre id="trace">[]</pre>
      </details>
      <details>
        <summary>Raw response</summary>
        <pre id="raw">{}</pre>
      </details>
    </div>
  </section>
</main>

<script>
const $ = (id) => document.getElementById(id);

function card(label, value, cls="") {
  return `<div class="card"><strong>${label}</strong><span class="${cls}">${value}</span></div>`;
}

async function fetchJSON(url, options={}) {
  const response = await fetch(url, options);
  const text = await response.text();
  let payload;
  try { payload = JSON.parse(text); }
  catch { payload = {detail: text || `HTTP ${response.status}`}; }
  if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
  return payload;
}

async function refreshStatus() {
  const cards = $("statusCards");
  try {
    const [live, ready, llm, vector, release] = await Promise.all([
      fetchJSON("/health/live"),
      fetchJSON("/health/ready"),
      fetchJSON("/api/v1/copilot/llm/status"),
      fetchJSON("/api/v1/copilot/vector/status"),
      fetchJSON("/api/v1/release/metrics")
    ]);
    cards.innerHTML = [
      card("API", `${live.status} · v${live.version}`, "good"),
      card("Database", `${ready.database} · PostGIS ${ready.postgis_version}`, "good"),
      card("AI provider", `${llm.planning_provider} · ${vector.embedding_model}`, "good"),
      card("Release", release.status === "ready"
        ? `${Math.round((release.aggregate_pass_rate || 0) * 100)}% benchmark checks`
        : "Build release metrics", release.status === "ready" ? "good" : "warn")
    ].join("");
  } catch (error) {
    cards.innerHTML = card("Status error", error.message, "bad");
  }
}

function normalizeResult(mode, payload) {
  if (mode === "llm") {
    return {
      answer: payload.run?.answer?.text || "No answer returned.",
      evidence: payload.run?.answer?.evidence || [],
      trace: payload.run?.tool_trace || []
    };
  }
  if (mode === "deterministic") {
    return {
      answer: payload.answer?.text || "No answer returned.",
      evidence: payload.answer?.evidence || [],
      trace: payload.tool_trace || []
    };
  }
  return {
    answer: payload.answer || "No answer returned.",
    evidence: payload.evidence || [],
    trace: payload.tool_trace || []
  };
}

function renderEvidence(items) {
  if (!items.length) return '<span class="muted">No evidence rows returned.</span>';
  return items.map((item, index) => {
    const value = item.values || item;
    return `<article><strong>Evidence ${index + 1}</strong><pre>${escapeHTML(JSON.stringify(value, null, 2))}</pre></article>`;
  }).join("");
}

function escapeHTML(value) {
  return value.replace(/[&<>"']/g, (char) => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#039;"
  })[char]);
}

async function runQuery() {
  const button = $("runButton");
  const state = $("requestState");
  const mode = $("mode").value;
  const provider = $("provider").value;
  const question = $("question").value.trim();
  const evidenceLimit = Number($("evidence").value);

  if (!question) return;
  button.disabled = true;
  state.textContent = "Running…";

  let endpoint;
  let body;
  if (mode === "llm") {
    endpoint = "/api/v1/copilot/llm/run";
    body = {question, provider, evidence_limit: evidenceLimit};
  } else if (mode === "deterministic") {
    endpoint = "/api/v1/copilot/agent/run";
    body = {question, evidence_limit: evidenceLimit};
  } else {
    endpoint = "/api/v1/copilot/vector/run";
    body = {question, top_k: 10, evidence_limit: evidenceLimit, min_similarity: 0.15};
  }

  try {
    const payload = await fetchJSON(endpoint, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)
    });
    const normalized = normalizeResult(mode, payload);
    $("answer").textContent = normalized.answer;
    $("evidenceRows").innerHTML = renderEvidence(normalized.evidence);
    $("trace").textContent = JSON.stringify(normalized.trace, null, 2);
    $("raw").textContent = JSON.stringify(payload, null, 2);
    state.textContent = "Completed.";
  } catch (error) {
    $("answer").textContent = error.message;
    $("evidenceRows").textContent = "No evidence.";
    $("trace").textContent = "[]";
    state.textContent = "Request failed.";
  } finally {
    button.disabled = false;
  }
}

$("runButton").addEventListener("click", runQuery);
$("refreshButton").addEventListener("click", refreshStatus);
$("mode").addEventListener("change", () => {
  $("provider").disabled = $("mode").value !== "llm";
});
document.querySelectorAll("[data-q]").forEach((button) => {
  button.addEventListener("click", () => {
    $("question").value = button.dataset.q;
    $("mode").value = button.dataset.mode;
    $("provider").disabled = $("mode").value !== "llm";
  });
});

refreshStatus();
</script>
</body>
</html>
"""


@router.get("/demo", response_class=HTMLResponse)
def demo() -> HTMLResponse:
    """Serve a dependency-free interactive portfolio demonstration."""

    return HTMLResponse(_DEMO_HTML)

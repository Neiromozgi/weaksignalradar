let currentRunId = null;

function modeHint(mode) {
  if (mode === "CACHE") return "CACHE / benchmark corpus (ft_bench_v1) — not LIVE jury result";
  if (mode === "SNAPSHOT") return "SNAPSHOT replay — no external source calls";
  return "LIVE — bounded OpenAlex + CORDIS + EPO attempts";
}

async function loadRuntime() {
  const [method, emb, llm, src] = await Promise.all([
    fetch("/api/v1/methodology/runtime").then((r) => r.json()),
    fetch("/api/v1/config/embedding").then((r) => r.json()),
    fetch("/api/v1/config/llm").then((r) => r.json()),
    fetch("/api/v1/config/sources").then((r) => r.json()),
  ]);
  document.getElementById("runtime").textContent = JSON.stringify(
    { methodology: method, embedding: emb, llm, sources: src.sources },
    null,
    2
  );
}

async function loadSnapshots() {
  const data = await fetch("/api/v1/snapshots").then((r) => r.json());
  const ul = document.getElementById("snapshots");
  ul.innerHTML = "";
  for (const s of data.snapshots || []) {
    const li = document.createElement("li");
    li.textContent = `${s.snapshot_id} (${s.mode || s.source}) immutable=${s.immutable}`;
    li.addEventListener("click", () => {
      document.getElementById("snapshotId").value = s.snapshot_id;
      document.getElementById("mode").value = "SNAPSHOT";
    });
    ul.appendChild(li);
  }
}

function renderFeatures(features) {
  if (!features) return "—";
  return Object.entries(features)
    .map(([k, v]) => `${k}: raw=${v.raw ?? "—"} pct=${v.percentile ?? "—"} avail=${v.availability}`)
    .join("\n");
}

async function showCandidate(runId, candidateId) {
  const c = await fetch(`/api/v1/analyses/${runId}/candidates/${candidateId}`).then((r) => r.json());
  const card = document.getElementById("card");
  card.textContent = JSON.stringify(
    {
      candidate_id: c.candidate_id,
      canonical_name: c.canonical_name,
      state: c.state,
      score: c.score,
      rank: c.rank,
      features: c.features,
      filters: c.filters,
      technical_signature: c.technical_signature,
      source_documents: c.source_documents,
      bootstrap: c.bootstrap,
    },
    null,
    2
  );
}

async function loadRegistries(runId, name) {
  const reg = await fetch(`/api/v1/analyses/${runId}/registries/${name}`).then((r) => r.json());
  const ul = document.getElementById("registry");
  ul.innerHTML = "";
  for (const c of reg.candidates || []) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>#${c.rank ?? "-"}</strong> ${c.canonical_name} score=${c.score ?? "n/a"}`;
    li.addEventListener("click", () => showCandidate(runId, c.candidate_id));
    ul.appendChild(li);
  }
}

async function loadRun(runId) {
  currentRunId = runId;
  const summary = await fetch(`/api/v1/analyses/${runId}`).then((r) => r.json());
  document.getElementById("status").textContent = `Run ${runId} — ${summary.status} — coverage: ${JSON.stringify(summary.coverage)}`;
  document.getElementById("modeLabel").textContent = modeHint(summary.data_mode);

  const docs = await fetch(`/api/v1/analyses/${runId}/documents`).then((r) => r.json());
  const docUl = document.getElementById("documents");
  docUl.innerHTML = "";
  for (const d of docs.documents || []) {
    const li = document.createElement("li");
    li.textContent = `${d.year || "?"} | ${d.title} | ${d.source_type} | ${d.coverage_state}`;
    docUl.appendChild(li);
  }

  const cands = await fetch(`/api/v1/analyses/${runId}/candidates?state=all`).then((r) => r.json());
  const candUl = document.getElementById("candidates");
  candUl.innerHTML = "";
  for (const c of cands.candidates || []) {
    const li = document.createElement("li");
    li.textContent = `${c.canonical_name} (${c.state}) score=${c.score ?? "n/a"}`;
    li.addEventListener("click", () => showCandidate(runId, c.candidate_id));
    candUl.appendChild(li);
  }

  await loadRegistries(runId, "top15");
}

async function runAnalysis() {
  const query = document.getElementById("query").value;
  const data_mode = document.getElementById("mode").value;
  const snapshot_id = document.getElementById("snapshotId").value || null;
  document.getElementById("status").textContent = "Running…";
  const resp = await fetch("/api/v1/analyses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      data_mode,
      score_profile_id: "ABCDE_v1",
      snapshot_id,
    }),
  });
  const body = await resp.json();
  if (!resp.ok) {
    document.getElementById("status").textContent = `Error ${resp.status}: ${JSON.stringify(body)}`;
    return;
  }
  await loadRun(body.run_id);
}

async function refreshSnapshot() {
  const query = document.getElementById("query").value;
  document.getElementById("status").textContent = "LIVE refresh…";
  const resp = await fetch("/api/v1/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  const body = await resp.json();
  if (!resp.ok) {
    document.getElementById("status").textContent = `Refresh error ${resp.status}: ${JSON.stringify(body)}`;
    return;
  }
  if (body.snapshot_id) {
    document.getElementById("snapshotId").value = body.snapshot_id;
    document.getElementById("mode").value = "SNAPSHOT";
  }
  document.getElementById("status").textContent = `Refresh ${body.refresh_id} snapshot=${body.snapshot_id || "none"}`;
  await loadSnapshots();
}

document.getElementById("runBtn").addEventListener("click", runAnalysis);
document.getElementById("refreshBtn").addEventListener("click", refreshSnapshot);
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    if (currentRunId) loadRegistries(currentRunId, btn.dataset.reg);
  });
});

loadRuntime();
loadSnapshots();

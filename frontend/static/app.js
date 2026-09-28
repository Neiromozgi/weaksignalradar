/** UI v1.0.3 — HOME → RUNNING → TOP-15 → Technology Card */

const state = {
  uiPhase: "IDLE",
  query: "",
  dataMode: "LIVE",
  snapshotId: "ft_bench_v1",
  runId: null,
  runSummary: null,
  view: "home",
  secondaryTab: "top15",
  selectedCandidateId: null,
  errorMessage: null,
};

const app = document.getElementById("app");
const secondaryNav = document.getElementById("secondaryNav");

function modeLabel(mode) {
  if (mode === "CACHE") return "CACHE / benchmark (не LIVE)";
  if (mode === "SNAPSHOT") return "SNAPSHOT (иммутабельный снимок)";
  return "LIVE";
}

function fmtVal(v) {
  if (v === null || v === undefined) return "UNKNOWN";
  return String(v);
}

function fmtNum(v) {
  if (v === null || v === undefined) return "UNKNOWN";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(3);
  return String(v);
}

function techLabel(c) {
  return c.display_label || c.canonical_name || "—";
}

function abcdeLine(features) {
  if (!features) return "";
  return ["A", "B", "C", "D", "E"]
    .map((code) => {
      const f = features[code] || {};
      return `${code}: ${fmtNum(f.percentile)} (${fmtVal(f.availability)})`;
    })
    .join(" · ");
}

function navHome() {
  state.view = "home";
  state.uiPhase = "IDLE";
  state.runId = null;
  state.runSummary = null;
  state.selectedCandidateId = null;
  state.errorMessage = null;
  secondaryNav.hidden = true;
  render();
}

function navTop15() {
  state.view = "top15";
  state.selectedCandidateId = null;
  render();
}

function showSecondary(name) {
  if (!state.runId) return;
  state.view = name;
  render();
}

async function apiPost(path, body) {
  const resp = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({}));
  return { ok: resp.ok, status: resp.status, data };
}

async function apiGet(path) {
  const resp = await fetch(path);
  const data = await resp.json().catch(() => ({}));
  return { ok: resp.ok, status: resp.status, data };
}

function deriveUiPhase(summary) {
  const st = summary.status;
  if (st === "FAILED") return "FAILED";
  if (st === "COMPLETED") {
    const cov = summary.coverage || {};
    const partialKeys = ["openalex", "cordis", "epo_lod"].filter(
      (k) => cov[k] && String(cov[k]).match(/PARTIAL|ERROR|UNAVAILABLE/i)
    );
    if (partialKeys.length) return "PARTIAL";
    return "COMPLETED";
  }
  return "RUNNING";
}

async function startAnalysis() {
  state.query = document.getElementById("queryInput")?.value?.trim() || state.query;
  state.dataMode = document.getElementById("modeSelect")?.value || state.dataMode;
  state.snapshotId = document.getElementById("snapshotInput")?.value?.trim() || state.snapshotId;
  state.uiPhase = "RUNNING";
  state.view = "running";
  state.errorMessage = null;
  render();

  const payload = {
    query: state.query,
    data_mode: state.dataMode,
    score_profile_id: "ABCDE_v1",
    snapshot_id: state.dataMode === "LIVE" ? null : state.snapshotId,
  };
  const { ok, status, data } = await apiPost("/api/v1/analyses", payload);
  if (!ok) {
    state.uiPhase = "FAILED";
    state.errorMessage =
      status === 503 && data.detail === "PERSISTENCE_UNAVAILABLE"
        ? "Сервис сохранения данных временно недоступен. Попробуйте позже."
        : `Ошибка анализа (${status}): ${data.detail || JSON.stringify(data)}`;
    state.view = "running";
    render();
    return;
  }
  state.runId = data.run_id;
  const summary = await apiGet(`/api/v1/analyses/${state.runId}`);
  state.runSummary = summary.data;
  state.uiPhase = deriveUiPhase(summary.data);
  state.view = "top15";
  secondaryNav.hidden = false;
  render();
}

function renderHome() {
  app.innerHTML = `
    <h2 class="screen-title">Главная</h2>
    <p class="hint">Введите отрасль или технологическое направление,
    в котором хотите найти ранние сигналы новых технологий</p>
    <label for="queryInput">Запрос</label>
    <input id="queryInput" type="text" value="${escapeHtml(state.query || "quantum photonic")}" />
    <div class="mode-settings">
      <strong>Дополнительно:</strong>
      <label>Режим
        <select id="modeSelect">
          <option value="LIVE" ${state.dataMode === "LIVE" ? "selected" : ""}>LIVE</option>
          <option value="CACHE" ${state.dataMode === "CACHE" ? "selected" : ""}>CACHE</option>
          <option value="SNAPSHOT" ${state.dataMode === "SNAPSHOT" ? "selected" : ""}>SNAPSHOT</option>
        </select>
      </label>
      <label>Snapshot ID (CACHE/SNAPSHOT)
        <input id="snapshotInput" type="text" value="${escapeHtml(state.snapshotId)}" />
      </label>
    </div>
    <button type="button" class="btn-primary" id="startBtn">Найти ранние сигналы</button>
  `;
  document.getElementById("startBtn").addEventListener("click", startAnalysis);
}

function renderRunning() {
  const fail = state.uiPhase === "FAILED";
  app.innerHTML = `
    <button type="button" class="btn-link" data-nav="home">← Вернуться на главную</button>
    <h2 class="screen-title">${fail ? "Ошибка обработки" : "Обработка запроса"}</h2>
    <p><strong>Запрос:</strong> ${escapeHtml(state.query)}</p>
    <p class="badge">${modeLabel(state.dataMode)}</p>
    ${
      fail
        ? `<div class="error-box">${escapeHtml(state.errorMessage || "Неизвестная ошибка")}</div>
           <button type="button" class="btn-primary" id="retryBtn">Повторить</button>`
        : `<div class="spinner"></div>
           <p>Мы обрабатываем ваш запрос.<br/>Анализ может занять несколько минут.</p>`
    }
  `;
  app.querySelector('[data-nav="home"]')?.addEventListener("click", navHome);
  document.getElementById("retryBtn")?.addEventListener("click", startAnalysis);
}

async function renderTop15() {
  if (!state.runId) {
    navHome();
    return;
  }
  const reg = await apiGet(`/api/v1/analyses/${state.runId}/registries/top15`);
  const candidates = reg.data.candidates || [];
  const summary = state.runSummary || (await apiGet(`/api/v1/analyses/${state.runId}`)).data;
  state.runSummary = summary;
  const phase = deriveUiPhase(summary);
  let partialNote = "";
  if (phase === "PARTIAL") {
    partialNote =
      '<p class="badge-warn badge">Частичный результат: один или несколько источников недоступны или ответили частично. Показаны только подтверждённые данные.</p>';
  }
  app.innerHTML = `
    <button type="button" class="btn-link" data-nav="home">← Вернуться на главную</button>
    <h2 class="screen-title">TOP-15 ранних сигналов новых технологий</h2>
    <p class="badge">${modeLabel(summary.data_mode)} · run ${escapeHtml(summary.run_id)}${
      summary.snapshot_id ? ` · snapshot ${escapeHtml(summary.snapshot_id)}` : ""
    }</p>
    ${partialNote}
    <p class="hint">Квалифицированных технологий: ${candidates.length} (без дополнения до 15)</p>
    <ul class="tech-list" id="topList"></ul>
  `;
  const ul = document.getElementById("topList");
  if (!candidates.length) {
    ul.innerHTML = "<li>Нет квалифицированных технологий в TOP-15 для этого прогона.</li>";
  }
  for (const c of candidates) {
    const li = document.createElement("li");
    li.innerHTML = `
      <div><span class="rank">#${fmtNum(c.rank)}</span> <strong>${escapeHtml(techLabel(c))}</strong></div>
      <div>Score: ${fmtNum(c.score)}</div>
      <div class="hint">${escapeHtml(c.early_signal_summary || "")}</div>
      <div class="abcde">${abcdeLine(c.features)}</div>
    `;
    li.addEventListener("click", () => {
      state.selectedCandidateId = c.candidate_id;
      state.view = "card";
      render();
    });
    ul.appendChild(li);
  }
  app.querySelector('[data-nav="home"]')?.addEventListener("click", navHome);
}

async function renderCard() {
  if (!state.runId || !state.selectedCandidateId) {
    navTop15();
    return;
  }
  const c = (await apiGet(`/api/v1/analyses/${state.runId}/candidates/${state.selectedCandidateId}`))
    .data;
  const summary = state.runSummary || (await apiGet(`/api/v1/analyses/${state.runId}`)).data;
  const sig = c.technical_signature || {};
  const filters = Array.isArray(c.filters) ? c.filters : [];
  const docs = c.source_documents || [];

  let featRows = "";
  for (const code of ["A", "B", "C", "D", "E"]) {
    const f = (c.features || {})[code] || {};
    featRows += `<tr>
      <th>${code}</th>
      <td>${fmtNum(f.raw)}</td>
      <td>${fmtNum(f.percentile)}</td>
      <td>${fmtNum(f.weight)}</td>
      <td>${fmtNum(f.contribution)}</td>
      <td>${fmtVal(f.availability)}</td>
    </tr>`;
  }

  let filterHtml = filters.length
    ? filters
        .map(
          (f) =>
            `<li>${escapeHtml(f.filter_code)} — ${f.passed ? "пройден" : "не пройден"} (${escapeHtml(f.reason_code || "")})</li>`
        )
        .join("")
    : "<li>Нет записей о фильтрах (кандидат прошёл базовые проверки).</li>";

  let docHtml = docs.length
    ? docs
        .map(
          (d) =>
            `<div class="doc-row"><strong>${escapeHtml(d.title || d.source_document_id)}</strong><br/>
            ${escapeHtml(d.source_type || "")} · ${escapeHtml(d.stable_external_id || "")}<br/>
            ${d.year || "—"} · ${escapeHtml(d.original_availability_status || "")}<br/>
            <a href="${escapeHtml(d.canonical_url || "#")}" target="_blank" rel="noopener">Источник</a>
            · snapshot ${escapeHtml(d.source_snapshot_id || "—")}</div>`
        )
        .join("")
    : "<p>Нет связанных документов.</p>";

  app.innerHTML = `
    <button type="button" class="btn-link" data-nav="top15">← Назад к TOP-15</button>
    <button type="button" class="btn-link" data-nav="home">← Вернуться на главную</button>
    <h2 class="screen-title">${escapeHtml(techLabel(c))}</h2>
    <p>Ранг: ${fmtNum(c.rank)} · Score: ${fmtNum(c.score)} · ${modeLabel(summary.data_mode)}</p>
    <p><strong>Название:</strong> ${escapeHtml(c.name_ru || c.canonical_name)}</p>
    <p><strong>Оригинальное / canonical name:</strong> ${escapeHtml(c.name_original || "—")}</p>
    <p><strong>Aliases / синонимы:</strong> ${escapeHtml((c.aliases || []).join(", ") || "—")}</p>
    <p class="hint">run_id: ${escapeHtml(summary.run_id)}${
      summary.snapshot_id ? ` · snapshot_id: ${escapeHtml(summary.snapshot_id)}` : ""
    }</p>

    <section class="card-section">
      <h3>Почему это ранний сигнал</h3>
      <p>${escapeHtml(c.early_signal_summary || "—")}</p>
    </section>

    <section class="card-section">
      <h3>Признаки A–E</h3>
      <table class="features"><thead><tr><th></th><th>raw</th><th>percentile</th><th>weight</th><th>contribution</th><th>status</th></tr></thead>
      <tbody>${featRows}</tbody></table>
    </section>

    <section class="card-section">
      <h3>Достаточность данных и фильтры</h3>
      <p>Stage: ${escapeHtml(c.state)} · Ranking: ${escapeHtml(c.ranking_status || "—")}</p>
      <ul>${filterHtml}</ul>
    </section>

    <section class="card-section">
      <h3>Техническая сигнатура</h3>
      <p>object: ${fmtVal(sig.object_class)} · mechanism: ${fmtVal(sig.mechanism)} · function: ${fmtVal(sig.function)}</p>
      <p>architecture: ${fmtVal(sig.architecture_or_process)} · property: ${fmtVal(sig.key_technical_property)}</p>
      <p>extraction: ${fmtVal(sig.extraction_status)}</p>
    </section>

    <section class="card-section">
      <h3>Evidence / sources</h3>
      ${docHtml}
    </section>

    <section class="card-section">
      <h3>Ограничения</h3>
      <ul>${(c.limitations_human || ["Нет дополнительных ограничений."])
        .map((line) => `<li>${escapeHtml(line)}</li>`)
        .join("")}</ul>
    </section>
  `;
  app.querySelector('[data-nav="home"]')?.addEventListener("click", navHome);
  app.querySelector('[data-nav="top15"]')?.addEventListener("click", navTop15);
}

async function renderAllResults() {
  const tabs = [
    ["top15", "TOP-15"],
    ["below15", "RANKED_BELOW_15"],
    ["rejected", "REJECTED"],
    ["insufficient", "UNKNOWN / INSUFFICIENT"],
  ];
  const tab = state.secondaryTab || "top15";
  const reg = await apiGet(`/api/v1/analyses/${state.runId}/registries/${tab}`);
  app.innerHTML = `
    <button type="button" class="btn-link" data-nav="home">← Вернуться на главную</button>
    <h2 class="screen-title">Все результаты</h2>
    <div class="tabs">${tabs
      .map(
        ([id, label]) =>
          `<button type="button" class="${id === tab ? "active" : ""}" data-tab="${id}">${label}</button>`
      )
      .join("")}</div>
    <ul class="tech-list" id="allList"></ul>
  `;
  app.querySelector('[data-nav="home"]')?.addEventListener("click", navHome);
  app.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.secondaryTab = btn.dataset.tab;
      render();
    });
  });
  const ul = document.getElementById("allList");
  for (const c of reg.data.candidates || []) {
    const li = document.createElement("li");
    li.textContent = `#${fmtNum(c.rank)} ${techLabel(c)} — score ${fmtNum(c.score)} (${c.ranking_status || c.state})`;
    li.addEventListener("click", () => {
      state.selectedCandidateId = c.candidate_id;
      state.view = "card";
      render();
    });
    ul.appendChild(li);
  }
}

async function renderDocuments() {
  const docs = (await apiGet(`/api/v1/analyses/${state.runId}/documents`)).data.documents || [];
  app.innerHTML = `
    <button type="button" class="btn-link" data-nav="home">← Вернуться на главную</button>
    <h2 class="screen-title">Документы (Source Document Registry)</h2>
    <div id="docList"></div>
  `;
  app.querySelector('[data-nav="home"]')?.addEventListener("click", navHome);
  const root = document.getElementById("docList");
  for (const d of docs) {
    const div = document.createElement("div");
    div.className = "doc-row";
    div.innerHTML = `<strong>${escapeHtml(d.title)}</strong><br/>
      ${escapeHtml(d.source_type)} · ID ${escapeHtml(d.stable_external_id)}<br/>
      ${d.year || "—"} · ${escapeHtml(d.coverage_state)} · ${escapeHtml(d.original_availability_status)}<br/>
      <a href="${escapeHtml(d.canonical_url)}" target="_blank" rel="noopener">${escapeHtml(d.canonical_url)}</a>`;
    root.appendChild(div);
  }
}

async function renderCandidates() {
  const cands = (await apiGet(`/api/v1/analyses/${state.runId}/candidates?state=all`)).data
    .candidates || [];
  app.innerHTML = `
    <button type="button" class="btn-link" data-nav="home">← Вернуться на главную</button>
    <h2 class="screen-title">Кандидаты (Candidate Registry)</h2>
    <ul class="tech-list" id="candList"></ul>
  `;
  app.querySelector('[data-nav="home"]')?.addEventListener("click", navHome);
  const ul = document.getElementById("candList");
  for (const c of cands) {
    const li = document.createElement("li");
    li.innerHTML = `${escapeHtml(techLabel(c))} · docs=${c.document_count} · orgs=${c.organization_count} · ${escapeHtml(c.ranking_status || c.state)}`;
    li.addEventListener("click", () => {
      state.selectedCandidateId = c.candidate_id;
      state.view = "card";
      render();
    });
    ul.appendChild(li);
  }
}

async function renderMethodology() {
  const [method, emb, llm, src] = await Promise.all([
    apiGet("/api/v1/methodology/runtime"),
    apiGet("/api/v1/config/embedding"),
    apiGet("/api/v1/config/llm"),
    apiGet("/api/v1/config/sources"),
  ]);
  app.innerHTML = `
    <button type="button" class="btn-link" data-nav="home">← Вернуться на главную</button>
    <h2 class="screen-title">Методология</h2>
    <section class="card-section">
      <h3>Что ищет СННИТ РАДАР</h3>
      <p>СННИТ РАДАР ищет ранние научно-технологические сигналы: направления, где уже есть воспроизводимые признаки новой технологии, но они ещё не стали зрелыми и массовыми.</p>
      <p>Система <strong>не гарантирует</strong> коммерческий успех и не утверждает, что каждая технология станет массовой.</p>
    </section>
    <section class="card-section">
      <h3>Признаки A–E (Score = 0.30A + 0.20B + 0.25C + 0.15D + 0.10E)</h3>
      <p><strong>A — Growth / Рост — 30%</strong> — растёт ли присутствие в релевантном корпусе.</p>
      <p><strong>B — Acceleration / Ускорение — 20%</strong> — ускоряется ли рост сигнала.</p>
      <p><strong>C — Content Novelty / Содержательная новизна — 25%</strong> — отличие механизма, функции, архитектуры и ключевых свойств.</p>
      <p><strong>D — Independent Confirmation / Независимое подтверждение — 15%</strong> — несколько независимых организаций и источников.</p>
      <p><strong>E — Weakness / Слабость сигнала — 10%</strong> — отличие раннего сигнала от уже зрелой технологии.</p>
      <p>Профиль: ${escapeHtml(method.data.score_profile_id)} (${escapeHtml(method.data.feature_contract_version)}).</p>
    </section>
    <section class="card-section">
      <h3>Реестры и TOP-15</h3>
      <p><strong>UNKNOWN / INSUFFICIENT</strong> — недостаточно данных для оценки.</p>
      <p><strong>REJECTED</strong> — данные есть, но критерии раннего сигнала не пройдены.</p>
      <p><strong>RANKED_BELOW_15</strong> — квалифицирован, но ниже первых 15.</p>
      <p>TOP-15 показывает <em>до</em> 15 лучших квалифицированных сигналов, без искусственного дополнения.</p>
    </section>
    <section class="card-section">
      <h3>Источники и режимы</h3>
      <p><strong>OpenAlex</strong> — основной reference-source для корпуса и временных рядов.</p>
      <p><strong>CORDIS/EURIO</strong> — проекты и независимое подтверждение (fail-soft).</p>
      <p><strong>EPO Linked Open Data</strong> — патентный источник (fail-soft).</p>
      <p><strong>LIVE</strong> — новый ограниченный запрос. <strong>CACHE</strong> — локальный benchmark. <strong>SNAPSHOT</strong> — неизменяемый набор для воспроизведения.</p>
      <ul>${(src.data.sources || [])
        .map((s) => `<li>${escapeHtml(s.source_id)}: ${escapeHtml(s.status)}</li>`)
        .join("")}</ul>
    </section>
    <section class="card-section">
      <h3>Runtime</h3>
      <p>Embedding: ${escapeHtml(emb.data.embedding_profile_id)} · ${escapeHtml(emb.data.runtime_status)} · ${escapeHtml(emb.data.active_backend || "—")}</p>
      <p>LLM extraction: ${escapeHtml(llm.data.profile_id)} · ${escapeHtml(llm.data.status)} · key ${escapeHtml(llm.data.openai_api_key)}</p>
    </section>
    <section class="card-section">
      <h3>UNKNOWN и ограничения</h3>
      <p>UNKNOWN не равен нулю — показатель нельзя корректно вычислить из имеющихся данных.</p>
      <p>Результат зависит от покрытия источников, качества метаданных, размера корпуса и evidence.</p>
    </section>
  `;
  app.querySelector('[data-nav="home"]')?.addEventListener("click", navHome);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function render() {
  if (state.view === "home") renderHome();
  else if (state.view === "running") renderRunning();
  else if (state.view === "top15") await renderTop15();
  else if (state.view === "card") await renderCard();
  else if (state.view === "all-results") await renderAllResults();
  else if (state.view === "documents") await renderDocuments();
  else if (state.view === "candidates") await renderCandidates();
  else if (state.view === "methodology") await renderMethodology();
}

secondaryNav.querySelectorAll("button").forEach((btn) => {
  btn.addEventListener("click", () => showSecondary(btn.dataset.view));
});

renderHome();

/** UI v2 — HOME → RUNNING → RESULTS → Technology Card (RU-first presentation) */

/**
 * Источники названий (GET …/candidates/…, presentation-only):
 * - name_ru_recorded — сырое CandidateRecord.name_ru до fallback (nullable).
 * - canonical_name, name_original — каноническое / English из прогона и naming.py.
 * - name_ru, display_label — fallback из naming.py; в UI заголовок НЕ строится из них.
 */

const RESULTS_TABS = [
  { id: "top15", label: "TOP-15" },
  { id: "all", label: "Все кандидаты" },
  { id: "rejected", label: "Отклонённые" },
  { id: "insufficient", label: "Недостаточно данных" },
  { id: "documents", label: "Документы" },
  { id: "methodology", label: "Методология" },
];

const state = {
  uiPhase: "IDLE",
  query: "",
  dataMode: "LIVE",
  snapshotId: "ft_bench_v1",
  runId: null,
  runSummary: null,
  view: "home",
  resultsTab: "top15",
  selectedCandidateId: null,
  errorMessage: null,
};

const app = document.getElementById("app");
const resultsTabsNav = document.getElementById("resultsTabs");

function modeLabel(mode) {
  if (mode === "CACHE") return "Режим CACHE (локальный benchmark, не LIVE)";
  if (mode === "SNAPSHOT") return "Режим SNAPSHOT (неизменяемый снимок)";
  return "Режим LIVE";
}

function modeBadgeClass(mode) {
  if (mode === "LIVE") return "badge badge-live";
  return "badge badge-offline";
}

function runningBodyText(mode) {
  if (mode === "LIVE") {
    return `<div class="spinner"></div>
      <p>Идёт LIVE-анализ: ограниченный поиск во внешних источниках и расчёт по методологии.<br/>Это может занять несколько минут.</p>`;
  }
  return `<div class="spinner"></div>
    <p>Идёт воспроизведение сохранённого корпуса (${mode === "CACHE" ? "CACHE" : "SNAPSHOT"}).<br/>
    Внешние источники и LLM-провайдер не вызываются — используются локальные snapshot/TMF cache.</p>`;
}

async function snapshotMetaHtml(summary) {
  const sid = summary.snapshot_id || summary.coverage?.snapshot_id;
  if (!sid) return "";
  let extra = "";
  const meta = await apiGet(`/api/v1/snapshots/${encodeURIComponent(sid)}`);
  if (meta.ok && meta.data) {
    const created = meta.data.created_at || meta.data.registered_at;
    if (created) extra = ` · создан ${escapeHtml(String(created))}`;
  }
  return `<p class="hint">Снимок данных: <strong>${escapeHtml(sid)}</strong>${extra}</p>`;
}

function offlineResultsNote(summary) {
  if (summary.data_mode === "LIVE") return "";
  if (summary.provenance?.offline_replay || summary.coverage?.offline_replay) {
    return `<p class="info-box compact">Сохранённый расчёт (${escapeHtml(summary.data_mode)}): без вызовов внешних источников и без LLM-провайдера. Результаты воспроизводятся из snapshot и кэша TMF.</p>`;
  }
  return "";
}

function recordedRussianName(c) {
  const v = c.name_ru_recorded;
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  return s || null;
}

function englishCanonicalName(c) {
  return String(c.name_original || c.canonical_name || "").trim() || null;
}

function technologyPresentation(c) {
  const ru = recordedRussianName(c);
  const en = englishCanonicalName(c);
  if (ru) {
    const heading = en ? `${ru} (${en})` : ru;
    return {
      heading,
      hasRecordedRu: true,
      ruText: ru,
      englishText: en,
      namingNote: null,
    };
  }
  const fallback = en || String(c.canonical_name || "").trim() || "—";
  return {
    heading: fallback,
    hasRecordedRu: false,
    ruText: null,
    englishText: en || fallback,
    namingNote: null,
  };
}

function techHeading(c) {
  return technologyPresentation(c).heading;
}

const REASON_RU = {
  MIN_WORKS_OR_ORGS: "мало документов или независимых организаций",
  HISTORY_TOO_SHORT: "слишком короткая история наблюдений",
  INSUFFICIENT: "недостаточно данных",
  SHARE_GTE_P90: "доля в корпусе на уровне зрелых технологий (≥ p90)",
  Q_GTE_0_10: "тренд слишком выражен для раннего сигнала (q ≥ 0,10)",
  AGE_GT_8: "наблюдаемый возраст сигнала больше 8 лет",
};

const FILTER_RU = {
  DATA_SUFFICIENCY: "Достаточность данных",
  MK_TREND: "Тренд Mann–Kendall",
  MAINSTREAM_SHARE: "Доля mainstream",
  OBSERVED_AGE: "Давность наблюдения",
};

const AVAIL_RU = {
  OK: "доступен",
  NOT_ESTIMATED: "не оценён",
  UNKNOWN: "неизвестно",
};

function translateReasonCode(code) {
  if (!code) return "причина не указана";
  return REASON_RU[code] || code;
}

function translateFilterCode(code) {
  if (!code) return "Фильтр";
  return FILTER_RU[code] || code;
}

function translateAvailability(av) {
  if (!av) return "—";
  return AVAIL_RU[av] || av;
}

function rankingStatusLabel(c) {
  const decision = c.decision_explanation?.decision;
  if (decision === "TOP15") return "TOP-15";
  if (decision === "RANKED_BELOW_15") return "Ниже TOP-15";
  const rs = c.ranking_status;
  if (rs === "UNKNOWN_INSUFFICIENT") return "Недостаточно данных";
  if (rs === "REJECTED") return "Отклонён";
  if (rs === "RANKED") {
    if (c.rank != null && c.rank <= 15) return "TOP-15";
    if (c.rank != null) return "Ниже TOP-15";
    return "Квалифицирован";
  }
  if (rs === "TOP15") return "TOP-15";
  if (rs === "RANKED_BELOW_15") return "Ниже TOP-15";
  return rs || c.state || "—";
}

function translateWhyLine(line) {
  const s = String(line || "");
  if (s.startsWith("INSUFFICIENT:")) {
    return `Недостаточно данных: ${translateReasonCode(s.slice("INSUFFICIENT:".length))}`;
  }
  if (s.startsWith("FILTER_REJECT:")) {
    const parts = s.split(":");
    const flt = translateFilterCode(parts[1]);
    const reason = translateReasonCode(parts[2]);
    return `Отклонён фильтром «${flt}»: ${reason}`;
  }
  if (s === "QUALIFIED:ABCDE_PERCENTILE_SCORE") return "Квалифицирован по баллу A–E (перцентили)";
  if (s === "RANK:TOP15") return "Входит в TOP-15";
  if (s === "RANK:BELOW_15") return "Ниже TOP-15";
  return s;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function isUnknownCandidate(c) {
  return (
    c.ranking_status === "UNKNOWN_INSUFFICIENT" ||
    c.state === "INSUFFICIENT" ||
    String(c.ranking_status || "").includes("INSUFFICIENT")
  );
}

function fmtScore(c) {
  if (isUnknownCandidate(c)) return "—";
  if (c.score === null || c.score === undefined) return "—";
  return typeof c.score === "number"
    ? Number.isInteger(c.score)
      ? String(c.score)
      : c.score.toFixed(3)
    : String(c.score);
}

function fmtRank(c) {
  if (isUnknownCandidate(c)) return "—";
  if (c.rank === null || c.rank === undefined) return "—";
  return String(c.rank);
}

function fmtNum(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(3);
  return String(v);
}

function insufficiencyReason(c) {
  const filters = Array.isArray(c.filters) ? c.filters : [];
  const failed = filters.filter(
    (f) => f.passed === false && (f.failure_class === "INSUFFICIENT" || f.filter_code === "DATA_SUFFICIENCY")
  );
  if (failed.length) {
    return failed
      .map(
        (f) =>
          `${translateFilterCode(f.filter_code || "DATA_SUFFICIENCY")}: ${translateReasonCode(f.reason_code || "INSUFFICIENT")}`
      )
      .join("; ");
  }
  const why = c.decision_explanation?.why_or_why_not;
  if (Array.isArray(why) && why.length) return why.map(translateWhyLine).join("; ");
  return "Недостаточно данных для оценки";
}

function abcdeLine(features) {
  if (!features) return "";
  return ["A", "B", "C", "D", "E"]
    .map((code) => {
      const f = features[code] || {};
      const pct = f.percentile;
      const pctStr = pct === null || pct === undefined ? "—" : fmtNum(pct);
      return `${code}: ${pctStr} (${translateAvailability(f.availability)})`;
    })
    .join(" · ");
}

function syncResultsTabsNav() {
  if (!state.runId || state.view === "home" || state.view === "running") {
    resultsTabsNav.hidden = true;
    resultsTabsNav.innerHTML = "";
    return;
  }
  resultsTabsNav.hidden = false;
  resultsTabsNav.innerHTML = RESULTS_TABS.map(
    (t) =>
      `<button type="button" class="${state.view === "results" && state.resultsTab === t.id ? "active" : ""}" data-tab="${t.id}">${t.label}</button>`
  ).join("");
  resultsTabsNav.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.view = "results";
      state.resultsTab = btn.dataset.tab;
      state.selectedCandidateId = null;
      render();
    });
  });
}

function navHome() {
  state.view = "home";
  state.uiPhase = "IDLE";
  state.runId = null;
  state.runSummary = null;
  state.selectedCandidateId = null;
  state.errorMessage = null;
  state.resultsTab = "top15";
  syncResultsTabsNav();
  render();
}

function navResults(tab) {
  state.view = "results";
  state.resultsTab = tab || state.resultsTab;
  state.selectedCandidateId = null;
  render();
}

function openCard(candidateId) {
  state.selectedCandidateId = candidateId;
  state.view = "card";
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
  if (st === "COMPLETED" || st === "PARTIAL") {
    const cov = summary.coverage || {};
    const partialKeys = ["openalex", "cordis", "epo_lod"].filter(
      (k) => cov[k] && String(cov[k]).match(/PARTIAL|ERROR|UNAVAILABLE/i)
    );
    if (partialKeys.length || st === "PARTIAL") return "PARTIAL";
    return "COMPLETED";
  }
  return "RUNNING";
}

function funnelFromSummary(summary, candidateTotal) {
  const prov = summary.provenance || {};
  const reg = summary.registries || {};
  const documents =
    prov.corpus_doc_count ??
    (Array.isArray(summary.documents) ? summary.documents.length : null);
  const mechanisms = prov.technology_mechanism_frame_count ?? null;
  const candidates = candidateTotal ?? null;
  const qualified =
    (reg.TOP15?.length || 0) + (reg.RANKED_BELOW_15?.length || 0);
  return { documents, mechanisms, candidates, qualified };
}

function renderFunnelHtml(funnel) {
  const steps = [
    { key: "documents", label: "Документы" },
    { key: "mechanisms", label: "Технологические механизмы" },
    { key: "candidates", label: "Кандидаты" },
    { key: "qualified", label: "Квалифицированные сигналы" },
  ];
  return `<div class="funnel" role="list">${steps
    .map(
      (s, i) => `<div class="funnel-step" role="listitem">
        <span class="funnel-value">${funnel[s.key] ?? "—"}</span>
        <span class="funnel-label">${s.label}</span>
        ${i < steps.length - 1 ? '<span class="funnel-arrow" aria-hidden="true">→</span>' : ""}
      </div>`
    )
    .join("")}</div>`;
}

async function ensureRunSummary() {
  if (!state.runId) return null;
  if (state.runSummary?.run_id === state.runId) return state.runSummary;
  const { data } = await apiGet(`/api/v1/analyses/${state.runId}`);
  state.runSummary = data;
  return data;
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
    const detail = data.detail || JSON.stringify(data);
    state.errorMessage =
      status === 503 && data.detail === "PERSISTENCE_UNAVAILABLE"
        ? "Сервис сохранения данных временно недоступен. Попробуйте позже или запустите CACHE/SNAPSHOT без PostgreSQL-сбоев."
        : state.dataMode === "LIVE" && status >= 500
          ? `LIVE-анализ недоступен (${status}). Проверьте сеть, ключи в .env или используйте CACHE/SNAPSHOT для офлайн-демо. ${detail}`
          : `Ошибка анализа (${status}): ${detail}`;
    state.view = "running";
    render();
    return;
  }
  state.runId = data.run_id;
  const summary = await apiGet(`/api/v1/analyses/${state.runId}`);
  state.runSummary = summary.data;
  state.uiPhase = deriveUiPhase(summary.data);
  state.view = "results";
  state.resultsTab = "top15";
  syncResultsTabsNav();
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
      <strong>Режим данных:</strong>
      <p class="hint">Для демонстрации без интернета/VPN выберите CACHE (benchmark <code>ft_bench_v1</code>) или SNAPSHOT.</p>
      <label>Режим
        <select id="modeSelect">
          <option value="LIVE" ${state.dataMode === "LIVE" ? "selected" : ""}>LIVE</option>
          <option value="CACHE" ${state.dataMode === "CACHE" ? "selected" : ""}>CACHE</option>
          <option value="SNAPSHOT" ${state.dataMode === "SNAPSHOT" ? "selected" : ""}>SNAPSHOT</option>
        </select>
      </label>
      <label>Идентификатор снимка (CACHE/SNAPSHOT)
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
    <p class="${modeBadgeClass(state.dataMode)}">${modeLabel(state.dataMode)}</p>
    ${
      fail
        ? `<div class="error-box">${escapeHtml(state.errorMessage || "Неизвестная ошибка")}</div>
           <button type="button" class="btn-primary" id="retryBtn">Повторить</button>`
        : runningBodyText(state.dataMode)
    }
  `;
  app.querySelector('[data-nav="home"]')?.addEventListener("click", navHome);
  document.getElementById("retryBtn")?.addEventListener("click", startAnalysis);
}

function candidateListItem(c) {
  const unknown = isUnknownCandidate(c);
  const li = document.createElement("li");
  li.className = unknown ? "candidate-unknown" : "";
  li.innerHTML = `
    <div class="cand-head">
      <span class="rank">${unknown ? "—" : `#${fmtRank(c)}`}</span>
      <strong>${escapeHtml(techHeading(c))}</strong>
    </div>
    <div class="cand-meta">
      Балл: ${fmtScore(c)} ·
      документов: ${c.document_count ?? "—"} ·
      организаций: ${c.organization_count ?? "—"} ·
      классов источников: ${c.source_class_count ?? "—"}
    </div>
    ${
      unknown
        ? `<div class="insufficiency">${escapeHtml(insufficiencyReason(c))}</div>`
        : `<div class="hint">${escapeHtml(c.early_signal_summary || "")}</div>
           <div class="abcde">${abcdeLine(c.features)}</div>`
    }
  `;
  li.addEventListener("click", () => openCard(c.candidate_id));
  return li;
}

async function renderResultsShell(summary, funnel, extraHtml) {
  const phase = deriveUiPhase(summary);
  let partialNote = "";
  if (phase === "PARTIAL") {
    partialNote =
      '<p class="badge-warn badge">Частичный результат: один или несколько источников недоступны или ответили частично. Показаны только подтверждённые данные.</p>';
  }
  app.innerHTML = `
    <button type="button" class="btn-link" data-nav="home">← Вернуться на главную</button>
    <h2 class="screen-title">Результаты анализа</h2>
    <p class="query-line"><strong>Запрос:</strong> ${escapeHtml(summary.normalized_query || state.query)}</p>
    <p class="${modeBadgeClass(summary.data_mode)}">${modeLabel(summary.data_mode)} · прогон ${escapeHtml(summary.run_id)}${
      summary.snapshot_id ? ` · снимок ${escapeHtml(summary.snapshot_id)}` : ""
    }</p>
    <div id="snapshotMeta"></div>
    ${offlineResultsNote(summary)}
    ${partialNote}
    ${renderFunnelHtml(funnel)}
    <div id="resultsBody">${extraHtml || ""}</div>
  `;
  const metaRoot = document.getElementById("snapshotMeta");
  if (metaRoot) {
    snapshotMetaHtml(summary).then((html) => {
      if (html) metaRoot.innerHTML = html;
    });
  }
  app.querySelector('[data-nav="home"]')?.addEventListener("click", navHome);
}

async function renderResults() {
  if (!state.runId) {
    navHome();
    return;
  }
  const summary = await ensureRunSummary();
  const tab = state.resultsTab || "top15";

  const allResp = await apiGet(`/api/v1/analyses/${state.runId}/candidates?state=all`);
  const allCandidates = allResp.data.candidates || [];
  const funnel = funnelFromSummary(summary, allCandidates.length);

  if (tab === "methodology") {
    await renderResultsMethodology(summary, funnel);
    return;
  }
  if (tab === "documents") {
    await renderResultsDocuments(summary, funnel);
    return;
  }

  let registryKey = tab;
  if (tab === "all") {
    await renderResultsShell(
      summary,
      funnel,
      `<h3 class="tab-title">Все кандидаты</h3><ul class="tech-list" id="tabList"></ul>`
    );
    const ul = document.getElementById("tabList");
    if (!allCandidates.length) {
      ul.innerHTML = '<li class="non-clickable">Кандидаты не обнаружены.</li>';
    } else {
      for (const c of allCandidates) ul.appendChild(candidateListItem(c));
    }
    return;
  }

  if (tab === "top15") registryKey = "top15";
  if (tab === "rejected") registryKey = "rejected";
  if (tab === "insufficient") registryKey = "insufficient";

  const reg = await apiGet(`/api/v1/analyses/${state.runId}/registries/${registryKey}`);
  const candidates = reg.data.candidates || [];
  const insufficientCount = (summary.registries?.UNKNOWN_INSUFFICIENT || []).length;
  const topEmpty = tab === "top15" && !candidates.length;

  let notice = "";
  if (topEmpty && insufficientCount > 0) {
    notice = `<div class="info-box">В текущем evidence set не найдено кандидатов, удовлетворяющих критериям достаточности данных. Обнаружено ${insufficientCount} технологических кандидатов, требующих дополнительного подтверждения. TOP-15 не заполняется искусственно.</div>`;
  } else if (topEmpty) {
    notice =
      '<div class="info-box">Квалифицированных сигналов в TOP-15 нет. Список не дополняется искусственно.</div>';
  }

  const titles = {
    top15: "TOP-15 ранних сигналов",
    rejected: "Отклонённые кандидаты",
    insufficient: "Недостаточно данных",
  };

  await renderResultsShell(
    summary,
    funnel,
    `${notice}<h3 class="tab-title">${titles[tab] || tab}</h3><ul class="tech-list" id="tabList"></ul>`
  );
  const ul = document.getElementById("tabList");
  if (!candidates.length && tab !== "top15") {
    ul.innerHTML = `<li class="non-clickable">Записей нет.</li>`;
  } else if (!candidates.length && tab === "top15") {
    /* message already in info-box */
  } else {
    for (const c of candidates) ul.appendChild(candidateListItem(c));
  }
}

async function renderResultsDocuments(summary, funnel) {
  const docs = (await apiGet(`/api/v1/analyses/${state.runId}/documents`)).data.documents || [];
  if (funnel.documents === null) funnel.documents = docs.length;
  await renderResultsShell(
    summary,
    funnel,
    `<h3 class="tab-title">Реестр документов</h3><div id="docList"></div>`
  );
  const root = document.getElementById("docList");
  if (!docs.length) {
    root.innerHTML = "<p>Документы не найдены.</p>";
    return;
  }
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

async function renderResultsMethodology(summary, funnel) {
  const [method, emb, llm, src] = await Promise.all([
    apiGet("/api/v1/methodology/runtime"),
    apiGet("/api/v1/config/embedding"),
    apiGet("/api/v1/config/llm"),
    apiGet("/api/v1/config/sources"),
  ]);
  const body = `
    <section class="card-section">
      <h3>Что ищет СННИТ РАДАР</h3>
      <p>СННИТ РАДАР ищет ранние научно-технологические сигналы: направления, где уже есть воспроизводимые признаки новой технологии, но они ещё не стали зрелыми и массовыми.</p>
      <p>Система <strong>не гарантирует</strong> коммерческий успех и не утверждает, что каждая технология станет массовой.</p>
    </section>
    <section class="card-section">
      <h3>Воронка результата</h3>
      <p>Документы → технологические механизмы → кандидаты → квалифицированные сигналы — сужение набора evidence без искусственного дополнения TOP-15.</p>
      ${renderFunnelHtml(funnel)}
    </section>
    <section class="card-section">
      <h3>Признаки A–E (балл = 0,30A + 0,20B + 0,25C + 0,15D + 0,10E)</h3>
      <p><strong>A — рост — 30%</strong> · <strong>B — ускорение — 20%</strong> · <strong>C — содержательная новизна — 25%</strong> · <strong>D — независимое подтверждение — 15%</strong> · <strong>E — слабость сигнала — 10%</strong></p>
      <p>Профиль: ${escapeHtml(method.data.score_profile_id)} (${escapeHtml(method.data.feature_contract_version)}).</p>
    </section>
    <section class="card-section">
      <h3>Реестры</h3>
      <p><strong>Недостаточно данных</strong> — недостаточно evidence; итоговый балл и ранг не присваиваются (в UI «—»).</p>
      <p><strong>Отклонён</strong> — данных достаточно, но критерии раннего сигнала не пройдены.</p>
      <p><strong>TOP-15</strong> и <strong>Ниже TOP-15</strong> — квалифицированные сигналы; в TOP-15 не более 15 без дополнения.</p>
    </section>
    <section class="card-section">
      <h3>Источники и среда выполнения</h3>
      <ul>${(src.data.sources || [])
        .map((s) => `<li>${escapeHtml(s.source_id)}: ${escapeHtml(s.status)}</li>`)
        .join("")}</ul>
      <p>Эмбеддинги: ${escapeHtml(emb.data.embedding_profile_id)} · ${escapeHtml(emb.data.runtime_status)}</p>
      <p>LLM-извлечение: ${escapeHtml(llm.data.profile_id)} · ${escapeHtml(llm.data.status)}</p>
    </section>
  `;
  await renderResultsShell(summary, funnel, body);
}

async function renderCard() {
  if (!state.runId || !state.selectedCandidateId) {
    navResults(state.resultsTab);
    return;
  }
  const c = (await apiGet(`/api/v1/analyses/${state.runId}/candidates/${state.selectedCandidateId}`))
    .data;
  const summary = await ensureRunSummary();
  const sig = c.technical_signature || {};
  const filters = Array.isArray(c.filters) ? c.filters : [];
  const docs = c.source_documents || [];
  const expl = c.decision_explanation || {};
  const unknown = isUnknownCandidate(c);
  const names = technologyPresentation(c);

  let featRows = "";
  for (const code of ["A", "B", "C", "D", "E"]) {
    const f = (c.features || {})[code] || {};
    featRows += `<tr>
      <th>${code}</th>
      <td>${fmtNum(f.raw)}</td>
      <td>${fmtNum(f.percentile)}</td>
      <td>${fmtNum(f.weight)}</td>
      <td>${fmtNum(f.contribution)}</td>
      <td>${escapeHtml(translateAvailability(f.availability))}</td>
    </tr>`;
  }

  let filterHtml = filters.length
    ? filters
        .map(
          (f) =>
            `<li>${escapeHtml(translateFilterCode(f.filter_code))} — ${f.passed ? "пройден" : "не пройден"} (${escapeHtml(translateReasonCode(f.reason_code))})</li>`
        )
        .join("")
    : "<li>Нет записей о фильтрах.</li>";

  let docHtml = docs.length
    ? docs
        .map(
          (d) =>
            `<div class="doc-row"><strong>${escapeHtml(d.title || d.source_document_id)}</strong><br/>
            ${escapeHtml(d.source_type || "")} · ${escapeHtml(d.stable_external_id || "")}<br/>
            ${d.year || "—"} · ${escapeHtml(d.original_availability_status || "")}<br/>
            ${(d.organization_names || []).length ? `Организации: ${escapeHtml(d.organization_names.join(", "))}<br/>` : ""}
            <a href="${escapeHtml(d.canonical_url || "#")}" target="_blank" rel="noopener">Источник</a>
            · снимок ${escapeHtml(d.source_snapshot_id || "—")}</div>`
        )
        .join("")
    : "<p>Нет связанных документов.</p>";

  const evidenceExamples = expl.evidence_examples || [];
  let spanHtml = evidenceExamples.length
    ? evidenceExamples
        .map(
          (ex) =>
            `<blockquote class="evidence-span">${escapeHtml(ex.evidence_span || ex.reason || "—")}<br/>
            <span class="hint">документ: ${escapeHtml(ex.doc_id || "—")}</span></blockquote>`
        )
        .join("")
    : "<p>Фрагменты evidence в записи не сохранены.</p>";

  const prov = summary.provenance || {};
  const provLines = [
    prov.discovery_method && `метод discovery: ${prov.discovery_method}`,
    prov.discovery_version && `версия: ${prov.discovery_version}`,
    prov.discovery_status && `статус: ${prov.discovery_status}`,
    prov.embedding_backend && `эмбеддинги: ${prov.embedding_backend}`,
  ]
    .filter(Boolean)
    .join(" · ");

  const nameBlock = names.hasRecordedRu
    ? `<p><strong>Русское название:</strong> ${escapeHtml(names.ruText)}</p>
       <p><strong>Каноническое (English):</strong> ${escapeHtml(names.englishText || "—")}</p>`
    : `<p><strong>Каноническое название:</strong> ${escapeHtml(names.englishText || names.heading)}</p>`;

  app.innerHTML = `
    <button type="button" class="btn-link" data-nav="results">← Назад к результатам</button>
    <button type="button" class="btn-link" data-nav="home">← Вернуться на главную</button>
    <h2 class="screen-title">${escapeHtml(names.heading)}</h2>
    <p>Ранг: ${fmtRank(c)} · Балл: ${fmtScore(c)} · ${modeLabel(summary.data_mode)}</p>
    <p><strong>Статус:</strong> ${escapeHtml(rankingStatusLabel(c))}</p>
    ${
      unknown
        ? `<div class="info-box"><strong>Причина:</strong> ${escapeHtml(insufficiencyReason(c))}</div>`
        : ""
    }
    ${nameBlock}
    <p><strong>Синонимы:</strong> ${escapeHtml((c.aliases || []).join(", ") || "—")}</p>
    <p class="hint">идентификатор прогона: ${escapeHtml(summary.run_id)} · документов ${c.document_count} · организаций ${c.organization_count} · классов источников ${c.source_class_count}</p>

    <section class="card-section">
      <h3>Фрагменты evidence</h3>
      ${spanHtml}
    </section>

    <section class="card-section">
      <h3>Обоснование раннего сигнала</h3>
      <p>${escapeHtml(c.early_signal_summary || expl.qualification_summary || "—")}</p>
      ${
        (expl.why_or_why_not || []).length
          ? `<ul>${expl.why_or_why_not.map((line) => `<li>${escapeHtml(translateWhyLine(line))}</li>`).join("")}</ul>`
          : ""
      }
    </section>

    <section class="card-section">
      <h3>Признаки A–E</h3>
      <table class="features"><thead><tr><th></th><th>сырое</th><th>перцентиль</th><th>вес</th><th>вклад</th><th>статус</th></tr></thead>
      <tbody>${featRows}</tbody></table>
      ${
        expl.sufficiency
          ? `<p class="hint">Достаточность: документы ${expl.sufficiency.documents?.value}/${expl.sufficiency.documents?.required} (${expl.sufficiency.documents?.status === "PASS" ? "выполнено" : "не выполнено"}) · организации ${expl.sufficiency.organizations?.value}/${expl.sufficiency.organizations?.required} (${expl.sufficiency.organizations?.status === "PASS" ? "выполнено" : "не выполнено"}) · временные точки ${expl.sufficiency.temporal_points?.value}/${expl.sufficiency.temporal_points?.required} (${expl.sufficiency.temporal_points?.status === "PASS" ? "выполнено" : "не выполнено"})</p>`
          : ""
      }
    </section>

    <section class="card-section">
      <h3>Фильтры и объяснение решения</h3>
      <ul>${filterHtml}</ul>
    </section>

    <section class="card-section">
      <h3>Происхождение прогона</h3>
      <p class="hint">${escapeHtml(provLines || "—")}</p>
    </section>

    <section class="card-section">
      <h3>Техническая сигнатура</h3>
      <p><strong>Объект:</strong> ${escapeHtml(String(sig.object_class ?? "—"))} · <strong>Механизм:</strong> ${escapeHtml(String(sig.mechanism ?? "—"))} · <strong>Функция:</strong> ${escapeHtml(String(sig.function ?? "—"))}</p>
      <p><strong>Архитектура / процесс:</strong> ${escapeHtml(String(sig.architecture_or_process ?? "—"))} · <strong>Свойство:</strong> ${escapeHtml(String(sig.key_technical_property ?? "—"))}</p>
      <p><strong>Статус извлечения:</strong> ${escapeHtml(String(sig.extraction_status || "—"))}</p>
    </section>

    <section class="card-section">
      <h3>Документы и ссылки на источники</h3>
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
  app.querySelector('[data-nav="results"]')?.addEventListener("click", () => navResults(state.resultsTab));
}

async function render() {
  syncResultsTabsNav();
  if (state.view === "home") renderHome();
  else if (state.view === "running") renderRunning();
  else if (state.view === "results") await renderResults();
  else if (state.view === "card") await renderCard();
  else {
    state.view = "results";
    await renderResults();
  }
}

renderHome();

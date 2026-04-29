const data = window.DASHBOARD_DATA;

const state = {
  activeScopeId: "cofidis-all",
  benchmarkMetric: "positive",
  brandFilter: "ALL",
  channelFilter: "ALL",
  sentimentFilter: "ALL",
  themeFilter: "ALL",
  search: "",
  reviewLimit: 18,
};

const lensOptions = [
  { id: "cofidis-all", label: "Tutta Cofidis" },
  { id: "cofidis-trustpilot", label: "Trustpilot" },
  { id: "cofidis-google-reviews", label: "Google Reviews" },
  { id: "cofidis-instagram-reels", label: "Instagram Reels" },
];

const benchmarkMetrics = [
  { id: "positive", label: "Quota positiva" },
  { id: "negative", label: "Quota negativa" },
  { id: "net", label: "Sentiment netto" },
];

const sentimentClassMap = {
  Positive: "positive",
  Neutral: "neutral",
  Negative: "negative",
};

const sentimentLabelMap = {
  Positive: "Positivo",
  Neutral: "Neutrale",
  Negative: "Negativo",
};

function pct(value) {
  return `${Number(value).toFixed(1)}%`;
}

function signed(value) {
  const formatted = Number(value).toFixed(1);
  return value > 0 ? `+${formatted}` : formatted;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function getScope(scopeId = state.activeScopeId) {
  return data.scopes[scopeId];
}

function getStory(scopeId = state.activeScopeId) {
  return data.story[scopeId] || data.story.overview;
}

function renderLensButtons() {
  const container = document.getElementById("lens-buttons");
  container.innerHTML = lensOptions
    .map(
      (lens) => `
        <button class="pill-button ${lens.id === state.activeScopeId ? "is-active" : ""}" data-scope="${lens.id}">
          ${lens.label}
        </button>
      `
    )
    .join("");

  container.querySelectorAll("[data-scope]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeScopeId = button.dataset.scope;
      render();
    });
  });
}

function renderHero() {
  const scope = getScope();
  const story = getStory();
  const title = document.getElementById("hero-title");
  const summary = document.getElementById("hero-summary");
  const net = document.getElementById("hero-net");
  const caption = document.getElementById("hero-caption");
  const sourceLabel = document.getElementById("source-label");
  const generatedLabel = document.getElementById("generated-label");

  title.textContent = story.headline;
  summary.textContent = story.summary;
  net.textContent = `${signed(scope.netSentiment)} pts`;
  net.className = `pulse-value ${scope.netSentiment >= 0 ? "pulse-positive" : "pulse-negative"}`;

  if (state.activeScopeId === "cofidis-all") {
    caption.textContent = `${scope.totalComments} commenti Cofidis da Trustpilot, Google Reviews e Instagram Reels`;
  } else {
    caption.textContent = `${scope.totalComments} commenti in questa vista`;
  }

  sourceLabel.textContent = `Fonti: ${data.meta.sources.join(" + ")}`;
  const generated = new Date(data.meta.generatedAt);
  generatedLabel.textContent = `Generato: ${generated.toLocaleString("it-IT", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })}`;
}

function renderKpis() {
  const scope = getScope();
  const highestRisk = data.channelComparison.reduce((best, item) =>
    item.priorityScore > best.priorityScore ? item : best
  );
  const topPositive = scope.topPositiveThemes[0];
  const topNegative = scope.topNegativeThemes[0];

  const cards = [
    {
      label: "Volume commenti",
      value: scope.totalComments.toLocaleString("it-IT"),
      meta:
        state.activeScopeId === "cofidis-all"
          ? "Voce dei clienti raccolta su tutti i canali Cofidis"
          : `Volume all'interno di ${scope.label}`,
    },
    {
      label: "Sentiment netto",
      value: `${signed(scope.netSentiment)} pts`,
      meta: `${pct(scope.rates.positive)} positivo vs ${pct(scope.rates.negative)} negativo`,
    },
    {
      label: "Principale driver positivo",
      value: topPositive ? topPositive.theme : "Nessun segnale",
      meta: topPositive ? `${topPositive.count} menzioni positive` : "Nessun tema rilevato",
    },
    {
      label: state.activeScopeId === "cofidis-all" ? "Canale prioritario" : "Principale punto critico",
      value: state.activeScopeId === "cofidis-all" ? highestRisk.channel : topNegative?.theme || "Nessun segnale",
      meta:
        state.activeScopeId === "cofidis-all"
          ? `${pct(highestRisk.rates.negative)} negativo, punteggio di intervento ${highestRisk.priorityScore}`
          : topNegative
            ? `${topNegative.count} menzioni negative`
            : "Nessun tema rilevato",
    },
  ];

  const container = document.getElementById("kpi-grid");
  container.innerHTML = cards
    .map(
      (card) => `
        <article class="card kpi-card">
          <div class="kpi-label">${escapeHtml(card.label)}</div>
          <h3 class="kpi-value">${escapeHtml(card.value)}</h3>
          <div class="kpi-meta">${escapeHtml(card.meta)}</div>
        </article>
      `
    )
    .join("");
}

function stackedBarMarkup(scope) {
  return `
    <div class="bar-track">
      <div class="bar-stack">
        <span class="segment-positive" style="width:${scope.rates.positive}%"></span>
        <span class="segment-neutral" style="width:${scope.rates.neutral}%"></span>
        <span class="segment-negative" style="width:${scope.rates.negative}%"></span>
      </div>
    </div>
    <div class="bar-labels">
      <span class="inline-metric inline-metric-positive">Positivo ${pct(scope.rates.positive)}</span>
      <span class="inline-metric inline-metric-neutral">Neutrale ${pct(scope.rates.neutral)}</span>
      <span class="inline-metric inline-metric-negative">Negativo ${pct(scope.rates.negative)}</span>
    </div>
  `;
}

function renderChannelComparison() {
  const container = document.getElementById("channel-comparison");
  container.className = "sentiment-list";
  container.innerHTML = data.channelComparison
    .map(
      (channel) => `
        <article class="sentiment-card ${channel.scopeId === state.activeScopeId ? "is-active" : ""}">
          <div class="row-head">
            <div>
              <h3>${escapeHtml(channel.channel)}</h3>
              <div class="review-meta">${channel.totalComments} commenti · sentiment netto ${escapeHtml(signed(channel.netSentiment))} pts</div>
            </div>
            <div class="chip chip-${channel.rates.negative >= 50 ? "negative" : channel.rates.positive >= 60 ? "positive" : "neutral"}">
              ${escapeHtml(channel.priorityScore ? `Priorità ${channel.priorityScore}` : `${pct(channel.rates.positive)} positivo`)}
            </div>
          </div>
          ${stackedBarMarkup(channel)}
        </article>
      `
    )
    .join("");
}

function renderInsight() {
  const story = getStory();
  const scope = getScope();
  const insightTitle = document.getElementById("insight-title");
  const insightSummary = document.getElementById("insight-summary");
  const actionList = document.getElementById("action-list");

  let dynamicLead = "";
  if (state.activeScopeId === "cofidis-all") {
    dynamicLead = `Su ${scope.totalComments} commenti Cofidis, il sentiment rimane polarizzato: ${pct(scope.rates.positive)} positivo e ${pct(scope.rates.negative)} negativo. Il principale driver di advocacy è ${data.highlights.topAdvocacyDriver.toLowerCase()}, mentre il più grande freno alla fiducia è ${data.highlights.topPainPoint.toLowerCase()}.`;
  } else {
    const topPositive = scope.topPositiveThemes[0];
    const topNegative = scope.topNegativeThemes[0];
    dynamicLead = `${scope.label} è attualmente a ${pct(scope.rates.positive)} positivo e ${pct(scope.rates.negative)} negativo. ${
      topPositive ? `${topPositive.theme} è il segnale positivo più forte.` : ""
    } ${topNegative ? `${topNegative.theme} è il principale punto di attrito.` : ""}`.trim();
  }

  insightTitle.textContent = story.headline;
  insightSummary.textContent = `${dynamicLead} ${story.summary}`;
  actionList.innerHTML = story.actions
    .map(
      (item, index) => `
        <div class="action-item" data-index="${index + 1}">
          ${item}
        </div>
      `
    )
    .join("");
}

function renderThemeColumn(targetId, items, total, tone) {
  const container = document.getElementById(targetId);
  container.className = "theme-list";
  if (!items.length) {
    container.innerHTML = `<div class="empty-state">Nessun tema emerso in questa vista.</div>`;
    return;
  }

  container.innerHTML = items
    .map((item) => {
      const ratio = total ? Math.max(8, (item.count / total) * 100) : 0;
      return `
        <div class="theme-item">
          <div class="theme-topline">
            <span>${escapeHtml(item.theme)}</span>
            <span class="review-meta">${escapeHtml(`${item.count} menzioni`)}</span>
          </div>
          <div class="theme-meter">
            <div class="theme-meter-fill segment-${tone}" style="width:${ratio}%"></div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderDrivers() {
  const scope = getScope();
  renderThemeColumn("positive-themes", scope.topPositiveThemes, scope.counts.positive, "positive");
  renderThemeColumn("negative-themes", scope.topNegativeThemes, scope.counts.negative, "negative");
}

function findQuoteReview(text, sentiment) {
  return data.reviews.find((review) => review.review === text && review.sentiment === sentiment) || null;
}

function renderQuotes() {
  const scope = getScope();
  const container = document.getElementById("quote-stack");
  const cards = ["Positive", "Negative", "Neutral"]
    .flatMap((sentiment) =>
      (scope.quotes[sentiment] || []).slice(0, 1).map((quote) => ({
        sentiment,
        quote,
        review: findQuoteReview(quote, sentiment),
      }))
    )
    .filter(Boolean);

  if (!cards.length) {
    container.innerHTML = `<div class="empty-state">Nessun commento rappresentativo è stato associato a questa vista.</div>`;
    return;
  }

  container.innerHTML = cards
    .map(
      (item) => `
        <article class="quote-card">
          <div class="quote-head">
            <h3>${escapeHtml(item.sentiment === 'Positive' ? 'Segnale positivo' : item.sentiment === 'Neutral' ? 'Segnale neutrale' : 'Segnale negativo')}</h3>
            <span class="chip chip-${sentimentClassMap[item.sentiment]}">${item.sentiment === 'Positive' ? 'Positivo' : item.sentiment === 'Neutral' ? 'Neutrale' : 'Negativo'}</span>
          </div>
          <blockquote>${escapeHtml(item.quote)}</blockquote>
          <div class="quote-source">
            ${escapeHtml(item.review ? `${item.review.brand} · ${item.review.channel} · ${item.review.name}` : scope.label)}
          </div>
        </article>
      `
    )
    .join("");
}

function benchmarkValue(scope) {
  if (state.benchmarkMetric === "positive") {
    return scope.rates.positive;
  }
  if (state.benchmarkMetric === "negative") {
    return scope.rates.negative;
  }
  return Math.max(scope.netSentiment + 100, 0) / 2;
}

function benchmarkDisplay(scope) {
  if (state.benchmarkMetric === "positive") {
    return `${pct(scope.rates.positive)} positivo`;
  }
  if (state.benchmarkMetric === "negative") {
    return `${pct(scope.rates.negative)} negativo`;
  }
  return `${signed(scope.netSentiment)} pts netti`;
}

function renderBenchmarkSwitch() {
  const container = document.getElementById("benchmark-switch");
  container.innerHTML = benchmarkMetrics
    .map(
      (metric) => `
        <button class="pill-button ${metric.id === state.benchmarkMetric ? "is-active" : ""}" data-benchmark-metric="${metric.id}">
          ${metric.label}
        </button>
      `
    )
    .join("");

  container.querySelectorAll("[data-benchmark-metric]").forEach((button) => {
    button.addEventListener("click", () => {
      state.benchmarkMetric = button.dataset.benchmarkMetric;
      renderBenchmark();
      renderBenchmarkSwitch();
    });
  });
}

function renderBenchmark() {
  const container = document.getElementById("benchmark-comparison");
  const rows = [...data.benchmarkComparison].sort((a, b) => benchmarkValue(b) - benchmarkValue(a));

  container.innerHTML = rows
    .map(
      (scope) => `
        <div class="benchmark-row">
          <div class="benchmark-brand">
            <h3>${escapeHtml(scope.brand)}</h3>
            <span class="chip chip-${scope.brand === "COFIDIS" ? "negative" : "positive"}">${escapeHtml(benchmarkDisplay(scope))}</span>
          </div>
          <div class="benchmark-meter">
            <div class="benchmark-fill" data-brand="${scope.brand}" style="width:${benchmarkValue(scope)}%"></div>
          </div>
          <div class="review-meta">${escapeHtml(`${scope.totalComments} commenti Trustpilot`)}</div>
        </div>
      `
    )
    .join("");

  const notes = document.getElementById("benchmark-notes");
  notes.innerHTML = data.benchmarkNotes
    .map(
      (note) => `
        <div class="note-card">${escapeHtml(note)}</div>
      `
    )
    .join("");
}

function renderManagementTable() {
  const container = document.getElementById("management-grid");
  container.innerHTML = data.managementTable
    .map(
      (item) => `
        <article class="management-card">
          <div class="theme-head">
            <h3>${escapeHtml(item.theme)}</h3>
          </div>
          <p>${escapeHtml(item.implication)}</p>
        </article>
      `
    )
    .join("");
}

function uniqueValues(key) {
  return [...new Set(data.reviews.map((review) => review[key]))].sort((a, b) => a.localeCompare(b));
}

function populateFilter(selectId, label, values, labelMap = {}) {
  const select = document.getElementById(selectId);
  select.innerHTML = [`<option value="ALL">Tutti i ${label}</option>`]
    .concat(
      values.map((value) => {
        const optionLabel = labelMap[value] || value;
        return `<option value="${escapeHtml(value)}">${escapeHtml(optionLabel)}</option>`;
      })
    )
    .join("");
}

function setupFilters() {
  populateFilter("brand-filter", "marchi", uniqueValues("brand"));
  populateFilter("channel-filter", "canali", uniqueValues("channel"));
  populateFilter(
    "sentiment-filter",
    "sentimenti",
    ["Positive", "Neutral", "Negative"],
    { Positive: "Positivo", Neutral: "Neutrale", Negative: "Negativo" }
  );
  populateFilter("theme-filter", "temi", data.themes);

  document.getElementById("brand-filter").addEventListener("change", (event) => {
    state.brandFilter = event.target.value;
    renderReviews();
  });
  document.getElementById("channel-filter").addEventListener("change", (event) => {
    state.channelFilter = event.target.value;
    renderReviews();
  });
  document.getElementById("sentiment-filter").addEventListener("change", (event) => {
    state.sentimentFilter = event.target.value;
    renderReviews();
  });
  document.getElementById("theme-filter").addEventListener("change", (event) => {
    state.themeFilter = event.target.value;
    renderReviews();
  });
  document.getElementById("search-filter").addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    renderReviews();
  });
}

function filteredReviews() {
  return data.reviews.filter((review) => {
    if (state.brandFilter !== "ALL" && review.brand !== state.brandFilter) return false;
    if (state.channelFilter !== "ALL" && review.channel !== state.channelFilter) return false;
    if (state.sentimentFilter !== "ALL" && review.sentiment !== state.sentimentFilter) return false;
    if (state.themeFilter !== "ALL" && !review.themes.includes(state.themeFilter)) return false;
    if (
      state.search &&
      !`${review.review} ${review.name} ${review.brand} ${review.channel}`.toLowerCase().includes(state.search)
    ) {
      return false;
    }
    return true;
  });
}

function renderReviews() {
  const reviews = filteredReviews();
  const count = document.getElementById("explorer-count");
  const container = document.getElementById("review-list");
  count.textContent = `${reviews.length.toLocaleString("it-IT")} commenti trovati`;

  const visible = reviews.slice(0, state.reviewLimit);
  if (!visible.length) {
    container.innerHTML = `<div class="empty-state">Nessun commento corrisponde a questa combinazione di filtri.</div>`;
    return;
  }

  container.innerHTML = visible
    .map(
      (review) => `
        <article class="review-card">
          <div class="review-head">
            <div>
              <h3>${escapeHtml(review.name)}</h3>
              <div class="review-meta">${escapeHtml(`${review.brand} · ${review.channel}${review.date ? ` · ${review.date}` : ""}`)}</div>
            </div>
            <span class="chip chip-${sentimentClassMap[review.sentiment]}">${sentimentLabelMap[review.sentiment] || review.sentiment}</span>
          </div>
          <blockquote>${escapeHtml(review.review)}</blockquote>
          <div class="review-chip-row">
            ${review.themes.map((theme) => `<span class="chip review-theme">${escapeHtml(theme)}</span>`).join("")}
          </div>
        </article>
      `
    )
    .join("");

  if (reviews.length > visible.length) {
    container.insertAdjacentHTML(
      "beforeend",
      `<div class="empty-state">Mostrati ${visible.length} di ${reviews.length} commenti. Affina i filtri per trovare altri o modifica il limite nel codice per visualizzarne di più.</div>`
    );
  }
}

function render() {
  renderLensButtons();
  renderHero();
  renderKpis();
  renderChannelComparison();
  renderInsight();
  renderDrivers();
  renderQuotes();
  renderBenchmarkSwitch();
  renderBenchmark();
  renderManagementTable();
  renderReviews();
}

setupFilters();
render();

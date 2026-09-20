(() => {
  const DATA = window.SUGAR_DATA;
  if (!DATA) {
    document.body.innerHTML = "<p style='padding:24px'>Dashboard data failed to load.</p>";
    return;
  }

  const METRICS = [
    { id: "production", label: "Production" },
    { id: "consumption", label: "Consumption" },
    { id: "export", label: "Exports" },
    { id: "import", label: "Imports" },
    { id: "ending", label: "Stocks" },
  ];
  const COLORS = {
    production: "#8fce72",
    consumption: "#7eb8d4",
    export: "#3fc1b0",
    import: "#e07a5f",
    ending: "#e0c36a",
  };

  const state = {
    yearIndex: DATA.years.length - 1,
    metric: "production",
    country: "Brazil",
  };
  const charts = {};

  Chart.defaults.color = "#9aa392";
  Chart.defaults.borderColor = "rgba(224, 195, 106, 0.12)";
  Chart.defaults.font.family = '"IBM Plex Sans", "Segoe UI", sans-serif';
  Chart.defaults.plugins.legend.labels.boxWidth = 10;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;

  function fmtKt(value) {
    if (value === null || value === undefined) return "—";
    return Number(value).toLocaleString("en-US");
  }

  function fmtMt(value, digits = 1) {
    if (value === null || value === undefined) return "—";
    return `${(value / 1000).toFixed(digits)} Mt`;
  }

  function fmtPct(value, digits = 1) {
    if (value === null || value === undefined) return "—";
    const sign = value > 0 ? "+" : "";
    return `${sign}${(value * 100).toFixed(digits)}%`;
  }

  function deltaClass(value) {
    if (value === null || value === undefined || value === 0) return "";
    return value > 0 ? "up" : "down";
  }

  function sparkPoints(values) {
    const nums = values.filter((value) => value !== null);
    const min = Math.min(...nums);
    const max = Math.max(...nums);
    const span = max - min || 1;
    return values
      .map((value, index) => {
        const x = (index / (values.length - 1)) * 100;
        const y = 26 - ((value - min) / span) * 22;
        return `${x},${y}`;
      })
      .join(" ");
  }

  function selectedTotals() {
    return DATA.kpis[state.yearIndex];
  }

  function rankingFor(metric, yearIndex, limit = 10) {
    const rows = DATA.countries
      .filter((country) => country.id !== "Other")
      .map((country) => {
        const value = DATA.series[country.id][metric][yearIndex];
        return value === null || value === undefined
          ? null
          : { id: country.id, name: country.name, value };
      })
      .filter(Boolean)
      .sort((a, b) => b.value - a.value || a.name.localeCompare(b.name));
    return rows.slice(0, limit);
  }

  function netTradeFor(yearIndex, limit = 12) {
    const rows = DATA.countries
      .filter((country) => country.id !== "Other")
      .map((country) => {
        const series = DATA.series[country.id];
        const exp = series.export[yearIndex];
        const imp = series.import[yearIndex];
        if (exp === null && imp === null) return null;
        const net = (exp || 0) - (imp || 0);
        return { name: country.name, net };
      })
      .filter(Boolean)
      .sort((a, b) => Math.abs(b.net) - Math.abs(a.net));
    return rows.slice(0, limit).sort((a, b) => a.net - b.net);
  }

  function upsertChart(id, config) {
    if (charts[id]) charts[id].destroy();
    const canvas = document.getElementById(id);
    charts[id] = new Chart(canvas, config);
  }

  function tooltipKt(context) {
    const label = context.dataset.label || "";
    return `${label}: ${fmtKt(context.parsed.y ?? context.parsed.x)} kt`;
  }

  function renderYearPills() {
    const root = document.getElementById("year-pills");
    root.innerHTML = DATA.yearLabels
      .map(
        (label, index) => `
          <button type="button" role="tab" data-year="${index}" aria-selected="${index === state.yearIndex}">
            ${label}
          </button>`
      )
      .join("");
    root.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        state.yearIndex = Number(button.dataset.year);
        renderAll();
      });
    });
  }

  function renderMetricTabs() {
    const root = document.getElementById("metric-tabs");
    root.innerHTML = METRICS.map(
      (metric) => `
        <button type="button" role="tab" data-metric="${metric.id}" aria-selected="${metric.id === state.metric}">
          ${metric.label}
        </button>`
    ).join("");
    root.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        state.metric = button.dataset.metric;
        renderAll();
      });
    });
  }

  function renderCountrySelect() {
    const select = document.getElementById("country-select");
    select.innerHTML = DATA.countries
      .map(
        (country) =>
          `<option value="${country.id}" ${country.id === state.country ? "selected" : ""}>${country.name}</option>`
      )
      .join("");
    select.addEventListener("change", () => {
      state.country = select.value;
      renderCountry();
    });
  }

  function renderKpis() {
    const kpi = selectedTotals();
    const cards = [
      ["Production", kpi.production, kpi.delta.production, DATA.totals.production],
      ["Consumption", kpi.consumption, kpi.delta.consumption, DATA.totals.consumption],
      ["Ending stocks", kpi.ending, kpi.delta.ending, DATA.totals.ending],
      ["Surplus", kpi.surplus, kpi.delta.surplus, DATA.totals.production.map((value, i) => value - DATA.totals.consumption[i])],
      ["Stock-to-use", kpi.stockToUse, kpi.delta.stockToUse, DATA.totals.ending.map((value, i) => value / DATA.totals.consumption[i])],
    ];
    document.getElementById("kpis").innerHTML = cards
      .map(([label, value, delta, series], index) => {
        const display = index === 4 ? `${(value * 100).toFixed(1)}%` : fmtMt(value);
        const deltaText =
          delta === null || delta === undefined
            ? "First year"
            : index === 4
              ? `${delta >= 0 ? "+" : ""}${(delta * 100).toFixed(1)} pt vs prior year`
              : `${delta >= 0 ? "+" : ""}${fmtMt(delta, 1)} vs prior year`;
        return `
          <article class="kpi">
            <p class="kpi-label">${label}</p>
            <p class="kpi-value">${display}</p>
            <p class="kpi-delta ${deltaClass(delta)}">${deltaText}</p>
            <svg class="spark" viewBox="0 0 100 28" aria-hidden="true">
              <polyline fill="none" stroke="${index === 2 || index === 4 ? COLORS.ending : COLORS.production}" stroke-width="2" points="${sparkPoints(series)}" />
            </svg>
          </article>`;
      })
      .join("");
  }

  function renderInsights() {
    document.getElementById("source-note").textContent = DATA.sourceNote;
    const kpi = selectedTotals();
    const brazil = DATA.series.Brazil.export[state.yearIndex] || 0;
    const top = rankingFor("production", state.yearIndex, 1)[0];
    const items = [
      {
        title: "Market tightness",
        body: `Stock-to-use is ${(kpi.stockToUse * 100).toFixed(1)}% in ${kpi.label}, versus ${((DATA.kpis[0].stockToUse) * 100).toFixed(1)}% in 2018/19.`,
      },
      {
        title: "Supply vs use",
        body: `World output of ${fmtMt(kpi.production)} ${kpi.surplus >= 0 ? "exceeds" : "falls short of"} consumption by ${fmtMt(Math.abs(kpi.surplus))}.`,
      },
      {
        title: "Export concentration",
        body: `Brazil accounts for ${((brazil / kpi.export) * 100).toFixed(0)}% of recorded world exports this year.`,
      },
      {
        title: "Largest producer",
        body: `${top.name} produces ${fmtMt(top.value)}, ${((top.value / kpi.production) * 100).toFixed(0)}% of the global total.`,
      },
    ];
    document.getElementById("insights").innerHTML = items
      .map(
        (item) => `
          <article class="insight">
            <h3>${item.title}</h3>
            <p>${item.body}</p>
          </article>`
      )
      .join("");
  }

  function renderBalanceChart() {
    const pointRadius = DATA.years.map((_, index) => (index === state.yearIndex ? 5 : 3));
    upsertChart("balance-chart", {
      type: "line",
      data: {
        labels: DATA.yearLabels,
        datasets: [
          {
            label: "Production",
            data: DATA.totals.production,
            borderColor: COLORS.production,
            backgroundColor: "transparent",
            tension: 0.3,
            yAxisID: "y",
            pointRadius,
          },
          {
            label: "Consumption",
            data: DATA.totals.consumption,
            borderColor: COLORS.consumption,
            backgroundColor: "transparent",
            tension: 0.3,
            yAxisID: "y",
            pointRadius,
          },
          {
            label: "Ending stocks",
            data: DATA.totals.ending,
            borderColor: COLORS.ending,
            backgroundColor: "rgba(224, 195, 106, 0.16)",
            fill: true,
            tension: 0.3,
            yAxisID: "y1",
            pointRadius,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          tooltip: { callbacks: { label: tooltipKt } },
        },
        scales: {
          y: {
            title: { display: true, text: "Production / use (kt)" },
            grid: { color: "rgba(224, 195, 106, 0.08)" },
          },
          y1: {
            position: "right",
            title: { display: true, text: "Stocks (kt)" },
            grid: { drawOnChartArea: false },
          },
        },
      },
    });
  }

  function renderRankChart() {
    const rows = rankingFor(state.metric, state.yearIndex, 10);
    const metricLabel = METRICS.find((metric) => metric.id === state.metric).label;
    document.getElementById("rank-caption").textContent =
      `Largest ${metricLabel.toLowerCase()} in ${DATA.yearLabels[state.yearIndex]}.`;
    upsertChart("rank-chart", {
      type: "bar",
      data: {
        labels: rows.map((row) => row.name),
        datasets: [
          {
            label: metricLabel,
            data: rows.map((row) => row.value),
            backgroundColor: COLORS[state.metric],
            borderRadius: 8,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: tooltipKt } },
        },
        scales: {
          x: {
            title: { display: true, text: "Thousand metric tons" },
            grid: { color: "rgba(224, 195, 106, 0.08)" },
          },
        },
      },
    });
  }

  function renderTradeChart() {
    const rows = netTradeFor(state.yearIndex, 12);
    upsertChart("trade-chart", {
      type: "bar",
      data: {
        labels: rows.map((row) => row.name),
        datasets: [
          {
            label: "Net exports",
            data: rows.map((row) => row.net),
            backgroundColor: rows.map((row) => (row.net >= 0 ? COLORS.export : COLORS.import)),
            borderRadius: 8,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => `${fmtKt(context.parsed.x)} kt net`,
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: "Net exports (kt)" },
            grid: { color: "rgba(224, 195, 106, 0.08)" },
          },
        },
      },
    });
  }

  function renderStocksChart() {
    const rows = DATA.stockChanges
      .filter((row) => row.id !== "Other")
      .slice(0, 8);
    upsertChart("stocks-chart", {
      type: "bar",
      data: {
        labels: rows.map((row) => row.name),
        datasets: [
          {
            label: "Change in ending stocks",
            data: rows.map((row) => row.delta),
            backgroundColor: COLORS.import,
            borderRadius: 8,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => {
                const row = rows[context.dataIndex];
                return `${fmtKt(row.delta)} kt (${fmtPct(row.pct, 0)})`;
              },
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: "kt change, 2018/19 to 2023/24" },
            grid: { color: "rgba(224, 195, 106, 0.08)" },
          },
        },
      },
    });
  }

  function renderCountry() {
    const profile = DATA.profiles[state.country];
    const series = profile.series;
    const idx = state.yearIndex;
    const production = series.production[idx];
    const consumption = series.consumption[idx];
    const exports = series.export[idx];
    const imports = series.import[idx];
    const ending = series.ending[idx];
    const net =
      exports === null && imports === null ? null : (exports || 0) - (imports || 0);
    const items = [
      ["Production", production],
      ["Consumption", consumption],
      ["Exports", exports],
      ["Imports", imports],
      ["Stocks", ending],
      ["Net trade", net],
    ];
    document.getElementById("profile-kpis").innerHTML = items
      .map(
        ([label, value]) => `
          <div>
            <dt>${label}</dt>
            <dd>${value === null || value === undefined ? "—" : fmtMt(value)}</dd>
          </div>`
      )
      .join("");

    const datasets = METRICS.map((metric) => ({
      label: metric.label,
      data: profile.series[metric.id],
      borderColor: COLORS[metric.id],
      backgroundColor: "transparent",
      tension: 0.3,
      spanGaps: true,
      hidden: !["production", "consumption", "ending"].includes(metric.id),
    }));
    upsertChart("country-chart", {
      type: "line",
      data: { labels: DATA.yearLabels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: { tooltip: { callbacks: { label: tooltipKt } } },
        scales: {
          y: {
            title: { display: true, text: "Thousand metric tons" },
            grid: { color: "rgba(224, 195, 106, 0.08)" },
          },
        },
      },
    });
  }

  function renderAll() {
    renderYearPills();
    renderMetricTabs();
    renderKpis();
    renderInsights();
    renderBalanceChart();
    renderRankChart();
    renderTradeChart();
    renderStocksChart();
    renderCountry();
  }

  document.getElementById("source-note").textContent = DATA.sourceNote;
  renderCountrySelect();
  renderAll();
})();

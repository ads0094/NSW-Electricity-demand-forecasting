const colors = { average: "#0b6b68", peak: "#d06b32", grid: "#e4e8e6", text: "#5e6c75" };

function formatNumber(value, digits = 0) {
  return new Intl.NumberFormat("en-AU", { maximumFractionDigits: digits }).format(value);
}

function lineChart(container, series, options = {}) {
  const width = Math.max(container.clientWidth || 760, 320);
  const height = options.height || 350;
  const margin = { top: 20, right: 18, bottom: 38, left: 58 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const all = series.flatMap(item => item.values.map(point => point.y));
  const minY = Math.min(...all) * 0.96;
  const maxY = Math.max(...all) * 1.03;
  const maxIndex = Math.max(...series.map(item => item.values.length - 1), 1);
  const x = index => margin.left + (index / maxIndex) * plotW;
  const y = value => margin.top + (1 - (value - minY) / (maxY - minY)) * plotH;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("aria-hidden", "true");
  for (let i = 0; i <= 4; i++) {
    const value = minY + (maxY - minY) * i / 4;
    const line = document.createElementNS(svg.namespaceURI, "line");
    line.setAttribute("x1", margin.left); line.setAttribute("x2", width - margin.right);
    line.setAttribute("y1", y(value)); line.setAttribute("y2", y(value)); line.setAttribute("class", "grid-line"); svg.append(line);
    const label = document.createElementNS(svg.namespaceURI, "text");
    label.setAttribute("x", margin.left - 8); label.setAttribute("y", y(value) + 4); label.setAttribute("text-anchor", "end"); label.setAttribute("class", "axis-label"); label.textContent = formatNumber(value); svg.append(label);
  }
  series.forEach(item => {
    const path = document.createElementNS(svg.namespaceURI, "path");
    const d = item.values.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(point.y).toFixed(1)}`).join(" ");
    path.setAttribute("d", d); path.setAttribute("fill", "none"); path.setAttribute("stroke", item.color); path.setAttribute("stroke-width", item.width || 2); path.setAttribute("vector-effect", "non-scaling-stroke"); svg.append(path);
  });
  const baseline = document.createElementNS(svg.namespaceURI, "line");
  baseline.setAttribute("x1", margin.left); baseline.setAttribute("x2", width - margin.right); baseline.setAttribute("y1", height - margin.bottom); baseline.setAttribute("y2", height - margin.bottom); baseline.setAttribute("class", "axis"); svg.append(baseline);
  const firstLabel = document.createElementNS(svg.namespaceURI, "text"); firstLabel.setAttribute("x", margin.left); firstLabel.setAttribute("y", height - 12); firstLabel.setAttribute("class", "axis-label"); firstLabel.textContent = options.firstLabel || ""; svg.append(firstLabel);
  const lastLabel = document.createElementNS(svg.namespaceURI, "text"); lastLabel.setAttribute("x", width - margin.right); lastLabel.setAttribute("y", height - 12); lastLabel.setAttribute("text-anchor", "end"); lastLabel.setAttribute("class", "axis-label"); lastLabel.textContent = options.lastLabel || ""; svg.append(lastLabel);
  container.replaceChildren(svg);
}

function barChart(container, rows) {
  const width = Math.max(container.clientWidth || 620, 320), height = 350;
  const margin = { top: 22, right: 70, bottom: 42, left: 130 };
  const plotW = width - margin.left - margin.right;
  const max = Math.max(...rows.map(row => row.mae_mw));
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  rows.forEach((row, index) => {
    const y = margin.top + index * 88;
    const label = document.createElementNS(svg.namespaceURI, "text"); label.setAttribute("x", margin.left - 12); label.setAttribute("y", y + 29); label.setAttribute("text-anchor", "end"); label.setAttribute("class", "axis-label"); label.textContent = row.model; svg.append(label);
    const rect = document.createElementNS(svg.namespaceURI, "rect"); rect.setAttribute("x", margin.left); rect.setAttribute("y", y); rect.setAttribute("width", row.mae_mw / max * plotW); rect.setAttribute("height", 42); rect.setAttribute("fill", index === rows.length - 1 ? colors.average : "#b9c7c4"); svg.append(rect);
    const value = document.createElementNS(svg.namespaceURI, "text"); value.setAttribute("x", margin.left + row.mae_mw / max * plotW + 9); value.setAttribute("y", y + 27); value.setAttribute("class", "axis-label"); value.textContent = `${formatNumber(row.mae_mw, 1)} MW`; svg.append(value);
  });
  container.replaceChildren(svg);
}

fetch("data/dashboard.json").then(response => response.json()).then(data => {
  const summary = data.summary;
  document.getElementById("records").textContent = formatNumber(summary.rows);
  document.getElementById("average-demand").textContent = `${formatNumber(summary.mean_mw)} MW`;
  document.getElementById("peak-demand").textContent = `${formatNumber(summary.peak_mw)} MW`;
  document.getElementById("test-mae").textContent = `${formatNumber(summary.test_mae_mw, 1)} MW`;
  document.getElementById("model-improvement").textContent = `${summary.baseline_improvement_percent}%`;

  const filter = document.getElementById("year-filter");
  data.annual.forEach(row => { const option = document.createElement("option"); option.value = row.year; option.textContent = row.year; filter.append(option); });
  function renderDaily() {
    const selected = filter.value;
    const rows = selected === "all" ? data.daily : data.daily.filter(row => row.date.startsWith(selected));
    const step = Math.max(1, Math.floor(rows.length / 900));
    const sampled = rows.filter((_, index) => index % step === 0 || index === rows.length - 1);
    lineChart(document.getElementById("daily-chart"), [
      { color: colors.average, values: sampled.map(row => ({ y: row.mean_mw })) },
      { color: colors.peak, values: sampled.map(row => ({ y: row.peak_mw })), width: 1.4 }
    ], { firstLabel: rows[0]?.date || "", lastLabel: rows.at(-1)?.date || "" });
  }
  filter.addEventListener("change", renderDaily); renderDaily();

  const seasonColors = { summer: "#d06b32", autumn: "#c99b38", winter: "#0b6b68", spring: "#6d8b75" };
  const seasons = ["summer", "autumn", "winter", "spring"];
  lineChart(document.getElementById("season-chart"), seasons.map(season => ({ color: seasonColors[season], values: data.seasonal.filter(row => row.season === season).map(row => ({ y: row.scheduled_demand_mw })) })), { height: 310, firstLabel: "00:00", lastLabel: "23:30" });
  const seasonalLegend = document.querySelector(".seasonal-legend");
  seasons.forEach(season => { const span = document.createElement("span"); span.textContent = season[0].toUpperCase() + season.slice(1); span.style.setProperty("--legend-color", seasonColors[season]); seasonalLegend.append(span); });
  barChart(document.getElementById("model-chart"), data.model_metrics);
}).catch(error => {
  document.getElementById("daily-chart").textContent = `Dashboard data could not be loaded: ${error.message}`;
});

window.addEventListener("resize", () => {
  document.getElementById("year-filter").dispatchEvent(new Event("change"));
});

/**
 * Talend Migration Discovery Dashboard
 *
 * Loads analysis data from analysis_output/ and renders charts/tables.
 * Data is populated by running the Python analysis scripts during a Devin session.
 */

const DATA_DIR = "../analysis_output";

const TIER_COLORS = {
  STRAIGHTFORWARD: "rgba(34, 197, 94, 0.7)",
  MODERATE: "rgba(234, 179, 8, 0.7)",
  COMPLEX: "rgba(239, 68, 68, 0.7)",
};

const COMPONENT_COLORS = [
  "#3b82f6", "#22c55e", "#eab308", "#ef4444", "#a855f7",
  "#f97316", "#06b6d4", "#ec4899", "#8b5cf6", "#14b8a6",
];

async function loadJSON(filename) {
  try {
    const resp = await fetch(`${DATA_DIR}/${filename}`);
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

function setCard(id, value) {
  const el = document.querySelector(`#${id} .card-value`);
  if (el) el.textContent = value;
}

function tierBadge(tier) {
  const cls = `badge badge-${tier.toLowerCase()}`;
  return `<span class="${cls}">${tier}</span>`;
}

function statusLabel(status) {
  const map = {
    NOT_STARTED: ["Not Started", "status-not-started"],
    IN_PROGRESS: ["In Progress", "status-in-progress"],
    COMPLETE: ["Complete", "status-complete"],
  };
  const [label, cls] = map[status] || [status, ""];
  return `<span class="${cls}">${label}</span>`;
}

function renderComponentChart(manifest) {
  const dist = manifest.component_distribution || {};
  const labels = Object.keys(dist);
  const values = Object.values(dist);

  new Chart(document.getElementById("component-chart"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: COMPONENT_COLORS.slice(0, labels.length),
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "right",
          labels: { color: "#e2e8f0", font: { size: 12 } },
        },
      },
    },
  });
}

function renderComplexityChart(manifest) {
  const domains = {};
  for (const job of manifest.jobs || []) {
    if (!domains[job.domain]) {
      domains[job.domain] = { STRAIGHTFORWARD: 0, MODERATE: 0, COMPLEX: 0 };
    }
    domains[job.domain][job.complexity.tier]++;
  }

  const labels = Object.keys(domains);
  const datasets = ["STRAIGHTFORWARD", "MODERATE", "COMPLEX"].map((tier) => ({
    label: tier.charAt(0) + tier.slice(1).toLowerCase(),
    data: labels.map((d) => domains[d][tier]),
    backgroundColor: TIER_COLORS[tier],
  }));

  new Chart(document.getElementById("complexity-chart"), {
    type: "bar",
    data: { labels, datasets },
    options: {
      responsive: true,
      scales: {
        x: {
          stacked: true,
          ticks: { color: "#94a3b8" },
          grid: { color: "rgba(51,65,85,0.5)" },
        },
        y: {
          stacked: true,
          beginAtZero: true,
          ticks: { color: "#94a3b8", stepSize: 1 },
          grid: { color: "rgba(51,65,85,0.5)" },
        },
      },
      plugins: {
        legend: { labels: { color: "#e2e8f0" } },
      },
    },
  });
}

function renderHeatmap(manifest) {
  const container = document.getElementById("heatmap");
  container.innerHTML = "";

  const jobs = [...(manifest.jobs || [])].sort(
    (a, b) => b.complexity.score - a.complexity.score
  );

  for (const job of jobs) {
    const tier = job.complexity.tier;
    let bg;
    if (tier === "COMPLEX") bg = "rgba(239,68,68,0.25)";
    else if (tier === "MODERATE") bg = "rgba(234,179,8,0.2)";
    else bg = "rgba(34,197,94,0.15)";

    const cell = document.createElement("div");
    cell.className = "heatmap-cell";
    cell.style.background = bg;
    cell.innerHTML = `
      <div>${job.complexity.score}</div>
      <div class="job-label">${job.job_name}</div>
    `;
    cell.title = `${job.domain}/${job.job_name}\nTier: ${tier}\nEffort: ${job.complexity.effort_hours}h\n${job.complexity.factors.join("\n")}`;
    container.appendChild(cell);
  }
}

function renderInventoryTable(manifest) {
  const tbody = document.getElementById("inventory-body");
  tbody.innerHTML = "";

  for (const job of manifest.jobs || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${job.domain}</td>
      <td>${job.job_name}</td>
      <td>${job.components.length}</td>
      <td>${job.connections.length}</td>
      <td>${tierBadge(job.complexity.tier)}</td>
      <td>${job.complexity.effort_hours}</td>
      <td>${statusLabel(job.conversion_status)}</td>
    `;
    tbody.appendChild(tr);
  }
}

function renderDependencyGraph(graph) {
  const container = document.getElementById("dependency-graph");
  container.innerHTML = "";

  const edges = graph.edges || [];
  if (edges.length === 0) {
    container.innerHTML = '<p class="empty-state">No cross-job dependencies detected.</p>';
    return;
  }

  for (const edge of edges) {
    const div = document.createElement("div");
    div.className = "dep-edge";
    div.innerHTML = `${edge.from}<span class="arrow">→</span>${edge.to} <span class="table-ref">via ${edge.via_table}</span>`;
    container.appendChild(div);
  }
}

function renderTMapAnalysis(inventory) {
  const tbody = document.getElementById("tmap-body");
  tbody.innerHTML = "";

  const expressions = [];
  for (const job of inventory) {
    for (const node of job.nodes || []) {
      if (node.component_name !== "tMap") continue;
      for (const expr of node.tmap_expressions || []) {
        if (expr.output_table === "__var__") continue;
        const len = expr.expression.length;
        let complexity;
        if (len > 100 || expr.expression.includes("?")) complexity = "High";
        else if (len > 50) complexity = "Medium";
        else complexity = "Low";
        expressions.push({
          job: `${job.domain}/${job.job_name}`,
          column: expr.column,
          expression: expr.expression,
          complexity,
        });
      }
    }
  }

  expressions.sort((a, b) => {
    const order = { High: 0, Medium: 1, Low: 2 };
    return order[a.complexity] - order[b.complexity];
  });

  for (const e of expressions.slice(0, 50)) {
    const tr = document.createElement("tr");
    const badge = e.complexity === "High" ? "badge-complex"
      : e.complexity === "Medium" ? "badge-moderate" : "badge-straightforward";
    tr.innerHTML = `
      <td>${e.job}</td>
      <td>${e.column}</td>
      <td><code>${escapeHtml(e.expression)}</code></td>
      <td><span class="badge ${badge}">${e.complexity}</span></td>
    `;
    tbody.appendChild(tr);
  }
}

function renderConversionProgress(manifest) {
  const jobs = manifest.jobs || [];
  const done = jobs.filter((j) => j.conversion_status === "COMPLETE").length;
  const pct = jobs.length > 0 ? Math.round((done / jobs.length) * 100) : 0;

  const bar = document.getElementById("conversion-progress");
  bar.style.width = `${pct}%`;
  bar.textContent = `${pct}% (${done}/${jobs.length})`;

  const tbody = document.getElementById("conversion-body");
  tbody.innerHTML = "";

  for (const job of jobs) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${job.domain}/${job.job_name}</td>
      <td>${statusLabel(job.conversion_status)}</td>
      <td>${job.converted_file || "—"}</td>
      <td>${job.test_file || "—"}</td>
    `;
    tbody.appendChild(tr);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function init() {
  const manifest = await loadJSON("migration_manifest.json");
  const inventory = await loadJSON("job_inventory.json");
  const graph = await loadJSON("dependency_graph.json");

  if (!manifest) {
    document.getElementById("status-text").textContent =
      "No analysis data found. Run discovery scripts to populate.";
    return;
  }

  // Update status
  document.getElementById("status-text").textContent = "Analysis data loaded";
  document.getElementById("generated-at").textContent =
    `Generated: ${manifest.generated_at || "unknown"}`;

  // Summary cards
  const s = manifest.summary || {};
  setCard("card-jobs", s.total_jobs || 0);
  setCard("card-components", s.total_components || 0);
  setCard("card-effort", s.total_effort_hours || 0);
  setCard("card-domains", (s.domains || []).length);

  // Charts
  renderComponentChart(manifest);
  renderComplexityChart(manifest);

  // Sections
  renderHeatmap(manifest);
  renderInventoryTable(manifest);
  renderConversionProgress(manifest);

  if (graph) renderDependencyGraph(graph);
  if (inventory) renderTMapAnalysis(inventory);
}

document.addEventListener("DOMContentLoaded", init);

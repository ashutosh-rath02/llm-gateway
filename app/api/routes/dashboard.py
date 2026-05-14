from textwrap import dedent

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


DASHBOARD_HTML = dedent(
    """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>LLM Gateway Dashboard</title>
      <style>
        :root {
          --bg: #f5efe4;
          --panel: rgba(255, 251, 244, 0.82);
          --panel-strong: rgba(255, 249, 240, 0.96);
          --ink: #1f1a17;
          --muted: #66594e;
          --accent: #115e59;
          --warn: #a8431f;
          --line: rgba(31, 26, 23, 0.1);
          --shadow: 0 24px 80px rgba(42, 27, 18, 0.12);
          --radius: 24px;
        }

        * {
          box-sizing: border-box;
        }

        body {
          margin: 0;
          min-height: 100vh;
          background:
            radial-gradient(
              circle at top left,
              rgba(17, 94, 89, 0.14),
              transparent 35%
            ),
            radial-gradient(
              circle at bottom right,
              rgba(168, 67, 31, 0.12),
              transparent 28%
            ),
            linear-gradient(180deg, #fbf5ea 0%, var(--bg) 100%);
          color: var(--ink);
          font-family: "Trebuchet MS", "Segoe UI", sans-serif;
        }

        .page {
          max-width: 1320px;
          margin: 0 auto;
          padding: 36px 20px 56px;
        }

        .hero {
          position: relative;
          overflow: hidden;
          padding: 36px;
          border-radius: 32px;
          background: linear-gradient(
            135deg,
            rgba(17, 94, 89, 0.94),
            rgba(8, 48, 46, 0.94)
          );
          color: #f9f4ec;
          box-shadow: var(--shadow);
        }

        .hero::after {
          content: "";
          position: absolute;
          inset: auto -10% -45% auto;
          width: 320px;
          height: 320px;
          border-radius: 999px;
          background: radial-gradient(
            circle,
            rgba(250, 232, 198, 0.3),
            transparent 70%
          );
          transform: rotate(12deg);
        }

        .hero h1 {
          margin: 0 0 12px;
          max-width: 720px;
          font-family: Georgia, "Times New Roman", serif;
          font-size: clamp(2.1rem, 4vw, 3.9rem);
          line-height: 0.98;
          letter-spacing: -0.04em;
        }

        .hero p {
          margin: 0;
          max-width: 760px;
          color: rgba(249, 244, 236, 0.82);
          font-size: 1rem;
          line-height: 1.6;
        }

        .chip-row {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin-top: 22px;
        }

        .chip {
          padding: 8px 12px;
          border-radius: 999px;
          border: 1px solid rgba(249, 244, 236, 0.16);
          background: rgba(249, 244, 236, 0.08);
          color: rgba(249, 244, 236, 0.92);
          font-size: 0.88rem;
        }

        .layout {
          display: grid;
          grid-template-columns: 340px minmax(0, 1fr);
          gap: 18px;
          margin-top: 22px;
        }

        .panel {
          background: var(--panel);
          border: 1px solid rgba(255, 255, 255, 0.65);
          border-radius: var(--radius);
          box-shadow: var(--shadow);
          backdrop-filter: blur(14px);
        }

        .controls {
          position: sticky;
          top: 16px;
          padding: 22px;
          align-self: start;
        }

        .controls h2,
        .workspace h2,
        .workspace h3 {
          margin: 0 0 12px;
          font-family: Georgia, "Times New Roman", serif;
          letter-spacing: -0.02em;
        }

        .controls p,
        .hint,
        .subtle {
          color: var(--muted);
          line-height: 1.5;
          font-size: 0.94rem;
        }

        .field {
          display: grid;
          gap: 8px;
          margin-top: 16px;
        }

        .field label {
          font-size: 0.82rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--muted);
        }

        input,
        button,
        pre {
          font: inherit;
        }

        input {
          width: 100%;
          padding: 12px 14px;
          border-radius: 14px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.8);
          color: var(--ink);
        }

        button {
          cursor: pointer;
          border: none;
          border-radius: 14px;
          padding: 12px 16px;
          color: #fff8ef;
          background: linear-gradient(135deg, #1a7d77, #115e59);
          transition: transform 120ms ease, opacity 120ms ease;
        }

        button:hover {
          transform: translateY(-1px);
          opacity: 0.97;
        }

        button.secondary {
          background: linear-gradient(135deg, #b56a37, #9a4f21);
        }

        .button-row {
          display: flex;
          gap: 10px;
          margin-top: 16px;
        }

        .status {
          margin-top: 18px;
          padding: 12px 14px;
          border-radius: 14px;
          background: rgba(17, 94, 89, 0.08);
          color: var(--ink);
          border: 1px solid rgba(17, 94, 89, 0.14);
          min-height: 48px;
        }

        .status.error {
          background: rgba(168, 67, 31, 0.08);
          border-color: rgba(168, 67, 31, 0.2);
          color: #6d2e18;
        }

        .workspace {
          display: grid;
          gap: 18px;
        }

        .section {
          padding: 22px;
        }

        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 12px;
          margin-top: 16px;
        }

        .metric-card {
          padding: 16px;
          border-radius: 18px;
          background: var(--panel-strong);
          border: 1px solid rgba(17, 94, 89, 0.08);
        }

        .metric-label {
          font-size: 0.76rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--muted);
        }

        .metric-value {
          margin-top: 8px;
          font-family: Georgia, "Times New Roman", serif;
          font-size: 2rem;
          letter-spacing: -0.04em;
        }

        .split {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 18px;
        }

        .table-wrap {
          overflow: auto;
          border-radius: 18px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.56);
        }

        table {
          width: 100%;
          border-collapse: collapse;
          min-width: 620px;
        }

        th,
        td {
          padding: 12px 14px;
          text-align: left;
          border-bottom: 1px solid var(--line);
          vertical-align: top;
        }

        th {
          font-size: 0.78rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--muted);
          background: rgba(17, 94, 89, 0.05);
        }

        td code,
        .trace-box code {
          font-family: "Consolas", "Courier New", monospace;
          font-size: 0.9rem;
        }

        .trace-box {
          padding: 18px;
          min-height: 260px;
          border-radius: 18px;
          background: linear-gradient(
            180deg,
            rgba(16, 25, 35, 0.97),
            rgba(20, 32, 41, 0.97)
          );
          color: #edf5f2;
          border: 1px solid rgba(255, 255, 255, 0.08);
          overflow: auto;
        }

        .trace-box pre {
          margin: 0;
          white-space: pre-wrap;
          word-break: break-word;
          line-height: 1.55;
        }

        .empty {
          color: var(--muted);
          padding: 26px 0 8px;
        }

        .ghost {
          color: var(--muted);
        }

        .actions button {
          padding: 8px 12px;
          border-radius: 10px;
          font-size: 0.9rem;
        }

        @media (max-width: 1080px) {
          .layout,
          .split,
          .metrics-grid {
            grid-template-columns: 1fr;
          }

          .controls {
            position: static;
          }
        }
      </style>
    </head>
    <body>
      <div class="page">
        <section class="hero">
          <h1>Gateway control room for traces, cost, and reliability.</h1>
          <p>
            This internal dashboard sits on top of the same protected APIs the
            gateway already exposes. Paste an API key, load live rollups, inspect
            recent traces, and jump straight into a trace id without leaving the
            browser.
          </p>
          <div class="chip-row">
            <div class="chip">No frontend build step</div>
            <div class="chip">Uses existing protected APIs</div>
            <div class="chip">Tenant and admin keys both supported</div>
          </div>
        </section>

        <div class="layout">
          <aside class="panel controls">
            <h2>Connect</h2>
            <p>
              Enter an API key used by the existing gateway auth flow. The page
              stores it only in this browser session.
            </p>

            <div class="field">
              <label for="api-key">API Key</label>
              <input
                id="api-key"
                type="password"
                placeholder="tenant-key or admin-key"
              />
            </div>

            <div class="field">
              <label for="tenant-filter">Tenant Filter</label>
              <input
                id="tenant-filter"
                type="text"
                placeholder="optional, admin only"
              />
            </div>

            <div class="field">
              <label for="trace-id">Trace Lookup</label>
              <input id="trace-id" type="text" placeholder="trace_..." />
            </div>

            <div class="button-row">
              <button id="load-dashboard" type="button">Load Dashboard</button>
              <button id="load-trace" class="secondary" type="button">
                Load Trace
              </button>
            </div>

            <div id="status" class="status">
              Waiting for a key. If auth is disabled locally, you can leave the
              key blank.
            </div>

            <p class="hint">
              Cost and reliability panels use the existing metrics endpoints.
              Recent traces come from the eval export endpoint so the dashboard
              stays aligned with persisted gateway behavior.
            </p>
          </aside>

          <main class="workspace">
            <section class="panel section">
              <h2>Overview</h2>
              <p class="subtle">
                A shared view of request volume, cost, success rate, fallback
                activity, and repair behavior.
              </p>
              <div id="metrics-grid" class="metrics-grid">
                <div class="metric-card">
                  <div class="metric-label">Requests</div>
                  <div id="metric-requests" class="metric-value">-</div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">Success Rate</div>
                  <div id="metric-success-rate" class="metric-value">-</div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">Fallback Rate</div>
                  <div id="metric-fallback-rate" class="metric-value">-</div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">Avg Cost</div>
                  <div id="metric-avg-cost" class="metric-value">-</div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">Repair Recovery</div>
                  <div id="metric-repair-rate" class="metric-value">-</div>
                </div>
              </div>
            </section>

            <section class="split">
              <section class="panel section">
                <h3>Cost by Feature</h3>
                <div id="cost-table" class="table-wrap"></div>
              </section>

              <section class="panel section">
                <h3>Reliability by Feature</h3>
                <div id="reliability-table" class="table-wrap"></div>
              </section>
            </section>

            <section class="panel section">
              <h3>Recent Traces</h3>
              <div id="recent-traces" class="table-wrap"></div>
            </section>

            <section class="panel section">
              <h3>Trace Detail</h3>
              <p class="subtle">
                Use the trace lookup field or click "Inspect" on a recent trace.
              </p>
              <div class="trace-box">
                <pre id="trace-detail">No trace loaded yet.</pre>
              </div>
            </section>
          </main>
        </div>
      </div>

      <script>
        const statusEl = document.getElementById("status");
        const apiKeyInput = document.getElementById("api-key");
        const tenantInput = document.getElementById("tenant-filter");
        const traceIdInput = document.getElementById("trace-id");

        apiKeyInput.value = sessionStorage.getItem("gateway_dashboard_api_key") || "";
        tenantInput.value =
          sessionStorage.getItem("gateway_dashboard_tenant_filter") || "";

        function setStatus(message, isError = false) {
          statusEl.textContent = message;
          statusEl.className = isError ? "status error" : "status";
        }

        function getApiKey() {
          return apiKeyInput.value.trim();
        }

        function getTenantFilter() {
          return tenantInput.value.trim();
        }

        function saveSessionState() {
          sessionStorage.setItem("gateway_dashboard_api_key", getApiKey());
          sessionStorage.setItem(
            "gateway_dashboard_tenant_filter",
            getTenantFilter()
          );
        }

        async function requestJson(path, options = {}) {
          saveSessionState();

          const headers = new Headers(options.headers || {});
          const apiKey = getApiKey();
          if (apiKey) {
            headers.set("X-API-Key", apiKey);
          }

          const response = await fetch(path, {
            ...options,
            headers,
          });

          let payload;
          try {
            payload = await response.json();
          } catch {
            payload = {
              detail: { message: "The server returned a non-JSON response." },
            };
          }

          if (!response.ok) {
            const detail = payload.detail || {};
            const message = detail.message || JSON.stringify(payload);
            throw new Error(message);
          }

          return payload;
        }

        function withTenantQuery(path) {
          const tenantId = getTenantFilter();
          if (!tenantId) {
            return path;
          }

          const separator = path.includes("?") ? "&" : "?";
          return `${path}${separator}tenant_id=${encodeURIComponent(tenantId)}`;
        }

        function formatMoney(value) {
          if (value === null || value === undefined) {
            return "-";
          }
          return `$${Number(value).toFixed(4)}`;
        }

        function formatPercent(value) {
          if (value === null || value === undefined) {
            return "-";
          }
          return `${(Number(value) * 100).toFixed(1)}%`;
        }

        function renderTable(containerId, columns, rows, emptyMessage) {
          const container = document.getElementById(containerId);
          if (!rows.length) {
            container.innerHTML = `<div class="empty">${emptyMessage}</div>`;
            return;
          }

          const header = columns
            .map((column) => `<th>${column.label}</th>`)
            .join("");
          const body = rows
            .map((row) => {
              const cells = columns
                .map((column) => `<td>${column.render(row)}</td>`)
                .join("");
              return `<tr>${cells}</tr>`;
            })
            .join("");

          container.innerHTML = [
            "<table><thead><tr>",
            header,
            "</tr></thead><tbody>",
            body,
            "</tbody></table>",
          ].join("");

          container.querySelectorAll("[data-trace-id]").forEach((button) => {
            button.addEventListener("click", () => {
              const traceId = button.getAttribute("data-trace-id");
              traceIdInput.value = traceId || "";
              loadTrace();
            });
          });
        }

        async function loadDashboard() {
          setStatus("Loading metrics and recent traces...");
          try {
            const [cost, reliability, recent] = await Promise.all([
              requestJson(withTenantQuery("/v1/metrics/cost")),
              requestJson(withTenantQuery("/v1/metrics/reliability")),
              requestJson("/v1/evals/export", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  tenant_id: getTenantFilter() || undefined,
                  limit: 12,
                }),
              }),
            ]);

            document.getElementById("metric-requests").textContent = String(
              cost.request_count ?? "-"
            );
            document.getElementById("metric-success-rate").textContent =
              formatPercent(reliability.success_rate);
            document.getElementById("metric-fallback-rate").textContent =
              formatPercent(reliability.fallback_rate);
            document.getElementById("metric-avg-cost").textContent =
              formatMoney(cost.avg_cost_usd);
            document.getElementById("metric-repair-rate").textContent =
              formatPercent(reliability.repair_recovery_rate);

            renderTable(
              "cost-table",
              [
                { label: "Feature", render: (row) => `<strong>${row.key}</strong>` },
                { label: "Requests", render: (row) => row.request_count },
                { label: "Success", render: (row) => row.success_count },
                {
                  label: "Total Cost",
                  render: (row) => formatMoney(row.total_cost_usd),
                },
                {
                  label: "Avg Cost",
                  render: (row) => formatMoney(row.avg_cost_usd),
                },
              ],
              cost.by_feature || [],
              "No cost data is available for the current filter."
            );

            renderTable(
              "reliability-table",
              [
                { label: "Feature", render: (row) => `<strong>${row.key}</strong>` },
                { label: "Requests", render: (row) => row.request_count },
                {
                  label: "Success Rate",
                  render: (row) => formatPercent(row.success_rate),
                },
                {
                  label: "Fallback Rate",
                  render: (row) => formatPercent(row.fallback_rate),
                },
                {
                  label: "Repair Recovery",
                  render: (row) => formatPercent(row.repair_recovery_rate),
                },
              ],
              reliability.by_feature || [],
              "No reliability data is available for the current filter."
            );

            renderTable(
              "recent-traces",
              [
                { label: "Trace", render: (row) => `<code>${row.trace_id}</code>` },
                {
                  label: "Feature",
                  render: (row) => row.feature || '<span class="ghost">-</span>',
                },
                {
                  label: "Status",
                  render: (row) => row.status || '<span class="ghost">-</span>',
                },
                {
                  label: "Model",
                  render: (row) => row.model || '<span class="ghost">-</span>',
                },
                {
                  label: "Cost",
                  render: (row) => formatMoney(row.cost_usd),
                },
                {
                  label: "Action",
                  render: (row) =>
                    [
                      '<span class="actions">',
                      `<button type="button" data-trace-id="${row.trace_id}">`,
                      "Inspect",
                      "</button>",
                      "</span>",
                    ].join(""),
                },
              ],
              recent.items || [],
              "No recent traces are available for the current filter."
            );

            setStatus("Dashboard data loaded successfully.");
          } catch (error) {
            setStatus(error.message || "Failed to load dashboard data.", true);
          }
        }

        async function loadTrace() {
          const traceId = traceIdInput.value.trim();
          if (!traceId) {
            setStatus("Enter a trace id before loading trace detail.", true);
            return;
          }

          setStatus(`Loading trace ${traceId}...`);
          try {
            const trace = await requestJson(
              `/v1/traces/${encodeURIComponent(traceId)}`
            );
            document.getElementById("trace-detail").textContent = JSON.stringify(
              trace,
              null,
              2
            );
            setStatus(`Trace ${traceId} loaded.`);
          } catch (error) {
            document.getElementById("trace-detail").textContent =
              "No trace loaded yet.";
            setStatus(error.message || "Failed to load trace detail.", true);
          }
        }

        document
          .getElementById("load-dashboard")
          .addEventListener("click", loadDashboard);
        document
          .getElementById("load-trace")
          .addEventListener("click", loadTrace);

        if (apiKeyInput.value) {
          loadDashboard();
        }
      </script>
    </body>
    </html>
    """
)


@router.get("/dashboard", response_class=HTMLResponse, tags=["dashboard"])
def dashboard() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_HTML)

let currentConfig = null;
let pendingExports = [];

async function api(path, options) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json();
  if (!res.ok || body.ok === false) {
    throw new Error(body.error || "Request failed");
  }
  return body;
}

function setFieldState(id, value, disabled) {
  const el = document.getElementById(id);
  el.value = value ?? "";
  el.disabled = !!disabled;
}

function renderExports() {
  const container = document.getElementById("exports-list");
  if (pendingExports.length === 0) {
    container.innerHTML = '<p class="hint">No exports configured yet.</p>';
    return;
  }
  container.innerHTML = pendingExports
    .map((exp, idx) => {
      const status = currentConfig?.lastStatusByName?.[exp.name];
      const badge = status
        ? status.ok
          ? `<span class="badge ok">${status.row_count} rows</span>`
          : `<span class="badge error">error</span>`
        : "";
      return `<div class="export-item">
        <div>
          <strong>${exp.name}</strong> — ${exp.entity_type}
          <div class="hint">${exp.fields.join(", ")} &rarr; ${exp.file_name}</div>
        </div>
        <div>${badge} <button data-idx="${idx}" class="remove-export">Remove</button></div>
      </div>`;
    })
    .join("");

  container.querySelectorAll(".remove-export").forEach((btn) => {
    btn.addEventListener("click", () => {
      pendingExports.splice(Number(btn.dataset.idx), 1);
      renderExports();
    });
  });
}

async function loadConfig() {
  currentConfig = await api("/api/config");
  const overrides = currentConfig.env_overrides || {};

  setFieldState("server_url", currentConfig.connection.server_url, overrides.server_url);
  setFieldState("script_name", currentConfig.connection.script_name, overrides.script_name);
  setFieldState(
    "script_secret",
    currentConfig.connection.script_secret_set ? "" : "",
    overrides.script_secret
  );
  document.getElementById("script_secret").placeholder = currentConfig.connection.script_secret_set
    ? "(unchanged if left blank)"
    : "(not set)";

  setFieldState("interval_minutes", currentConfig.interval_minutes, overrides.interval_minutes);

  pendingExports = currentConfig.exports.map((e) => ({
    name: e.name,
    entity_type: e.entity_type,
    fields: e.fields,
    file_name: e.file_name,
    filters: e.filters || [],
  }));
  document.getElementById("add-export").disabled = !!overrides.exports;
  document.getElementById("save-config").disabled = false;
  renderExports();
}

async function refreshStatus() {
  const status = await api("/api/status");
  const el = document.getElementById("status");
  const lines = [];
  lines.push(status.running ? "Running now…" : "Idle");
  if (status.last_run_at) {
    lines.push(`Last run: ${new Date(status.last_run_at * 1000).toLocaleString()}`);
  }
  if (status.last_error) {
    lines.push(`<span class="badge error">Last error: ${status.last_error}</span>`);
  } else if (status.last_success_at) {
    lines.push(`<span class="badge ok">Last success: ${new Date(status.last_success_at * 1000).toLocaleString()}</span>`);
  }
  if (status.next_run_at) {
    lines.push(`Next run: ${new Date(status.next_run_at * 1000).toLocaleString()}`);
  }
  el.innerHTML = lines.join("<br/>");

  if (currentConfig) {
    currentConfig.lastStatusByName = status.per_export;
    renderExports();
  }
}

function currentConnectionFromForm() {
  const secret = document.getElementById("script_secret").value;
  return {
    server_url: document.getElementById("server_url").value,
    script_name: document.getElementById("script_name").value,
    script_secret: secret || undefined,
  };
}

document.getElementById("test-connection").addEventListener("click", async () => {
  const resultEl = document.getElementById("connection-result");
  resultEl.textContent = "Testing…";
  try {
    const connection = { ...currentConnectionFromForm() };
    if (!connection.script_secret) delete connection.script_secret;
    await api("/api/connection/test", { method: "POST", body: JSON.stringify({ connection }) });
    resultEl.innerHTML = '<span class="badge ok">Connected</span>';
  } catch (err) {
    resultEl.innerHTML = `<span class="badge error">${err.message}</span>`;
  }
});

document.getElementById("load-entities").addEventListener("click", async () => {
  const select = document.getElementById("entity-select");
  select.innerHTML = "<option>Loading…</option>";
  try {
    const { entities } = await api("/api/schema/entities");
    select.innerHTML = entities
      .map((e) => `<option value="${e.entity_type}">${e.display_name} (${e.entity_type})</option>`)
      .join("");
    select.dispatchEvent(new Event("change"));
  } catch (err) {
    select.innerHTML = `<option>Failed: ${err.message}</option>`;
  }
});

document.getElementById("entity-select").addEventListener("change", async (e) => {
  const entityType = e.target.value;
  const fieldsSelect = document.getElementById("fields-select");
  if (!entityType) return;
  fieldsSelect.innerHTML = "<option>Loading…</option>";
  try {
    const { fields } = await api(`/api/schema/fields/${encodeURIComponent(entityType)}`);
    fieldsSelect.innerHTML = fields
      .map((f) => `<option value="${f.field_name}">${f.display_name} (${f.field_name})</option>`)
      .join("");
  } catch (err) {
    fieldsSelect.innerHTML = `<option>Failed: ${err.message}</option>`;
  }
});

document.getElementById("add-export").addEventListener("click", () => {
  const entityType = document.getElementById("entity-select").value;
  const fieldsSelect = document.getElementById("fields-select");
  const fields = Array.from(fieldsSelect.selectedOptions).map((o) => o.value);
  const fileNameInput = document.getElementById("file-name");
  let fileName = fileNameInput.value.trim();

  if (!entityType || fields.length === 0) {
    alert("Pick an entity type and at least one field.");
    return;
  }
  if (!fileName) fileName = `${entityType.toLowerCase()}.csv`;
  if (!fileName.endsWith(".csv")) fileName += ".csv";

  pendingExports.push({
    name: fileName.replace(/\.csv$/, ""),
    entity_type: entityType,
    fields,
    file_name: fileName,
    filters: [],
  });
  fileNameInput.value = "";
  renderExports();
});

document.getElementById("save-config").addEventListener("click", async () => {
  const resultEl = document.getElementById("save-result");
  resultEl.textContent = "Saving…";
  try {
    const connection = currentConnectionFromForm();
    if (!connection.script_secret) delete connection.script_secret;
    const payload = {
      connection,
      interval_minutes: Number(document.getElementById("interval_minutes").value) || 10,
      exports: pendingExports,
    };
    await api("/api/config", { method: "POST", body: JSON.stringify(payload) });
    resultEl.innerHTML = '<span class="badge ok">Saved</span>';
    await loadConfig();
  } catch (err) {
    resultEl.innerHTML = `<span class="badge error">${err.message}</span>`;
  }
});

document.getElementById("run-now").addEventListener("click", async () => {
  await api("/api/run-now", { method: "POST" });
  setTimeout(refreshStatus, 1000);
});

loadConfig();
refreshStatus();
setInterval(refreshStatus, 10000);

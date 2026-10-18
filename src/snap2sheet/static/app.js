const fileInput = document.getElementById("files");
const drop = document.getElementById("drop");
const fileList = document.getElementById("file-list");
const ocr = document.getElementById("ocr");
const scanButton = document.getElementById("scan");
const statusLine = document.getElementById("status");
const result = document.getElementById("result");
const resultTitle = document.getElementById("result-title");
const summary = document.getElementById("summary");
const rowsBody = document.getElementById("rows");
const validation = document.getElementById("validation");
const csvButton = document.getElementById("csv");
const xlsxButton = document.getElementById("xlsx");

const MAX_BYTES = 15 * 1024 * 1024;
const state = { files: [], receipts: new Map() };

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value < 10 && unit > 0 ? value.toFixed(1) : Math.round(value)} ${units[unit]}`;
}

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setStatus(message, isError = false) {
  statusLine.textContent = message;
  statusLine.classList.toggle("is-error", isError);
}

function addFiles(files) {
  for (const file of files) {
    if (!file) continue;
    if (file.size > MAX_BYTES) {
      setStatus(`${file.name} is larger than 15 MB and was skipped.`, true);
      continue;
    }
    state.files.push(file);
  }
  renderFileList();
}

function renderFileList() {
  fileList.innerHTML = state.files
    .map(
      (file, index) => `<li class="file-item">
        <span class="file-name">${escapeHtml(file.name)} <span class="meta">${formatBytes(file.size)}</span></span>
        <button class="remove" type="button" data-index="${index}">Remove</button>
      </li>`
    )
    .join("");
  if (state.files.length) setStatus(`${state.files.length} file${state.files.length === 1 ? "" : "s"} ready.`);
}

fileInput.addEventListener("change", () => {
  addFiles(fileInput.files);
  fileInput.value = "";
});

fileList.addEventListener("click", (event) => {
  const button = event.target.closest(".remove");
  if (!button) return;
  state.files.splice(Number(button.dataset.index), 1);
  renderFileList();
});

["dragenter", "dragover"].forEach((eventName) => {
  drop.addEventListener(eventName, (event) => {
    event.preventDefault();
    drop.classList.add("is-over");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  drop.addEventListener(eventName, (event) => {
    event.preventDefault();
    drop.classList.remove("is-over");
  });
});

drop.addEventListener("drop", (event) => {
  addFiles(event.dataTransfer.files);
});

document.addEventListener("paste", (event) => {
  const items = event.clipboardData ? event.clipboardData.items : [];
  const pasted = [];
  for (const item of items) {
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) pasted.push(file);
    }
  }
  if (pasted.length) {
    addFiles(pasted);
    setStatus("Pasted image added. Click Scan receipts.");
  }
});

function totalLabel(receipts) {
  const totals = new Map();
  for (const receipt of receipts.values()) {
    const row = document.querySelector(`tr[data-key="${receipt.key}"]`);
    const currency =
      (row && row.querySelector('[data-field="currency"]').value.trim().toUpperCase()) ||
      receipt.currency ||
      "";
    const value = Number(
      row ? row.querySelector('[data-field="total"]').value : receipt.total
    );
    if (!Number.isFinite(value)) continue;
    totals.set(currency, (totals.get(currency) || 0) + value);
  }
  return Array.from(totals.entries())
    .map(([currency, value]) => `${currency || "?"} ${value.toFixed(2)}`)
    .join(" · ");
}

function countDuplicates() {
  let count = 0;
  for (const receipt of state.receipts.values()) {
    if (receipt.duplicate) count += 1;
  }
  return count;
}

function updateSummary() {
  const count = state.receipts.size;
  const totals = totalLabel(state.receipts);
  const duplicates = countDuplicates();
  const parts = [`${count} receipt${count === 1 ? "" : "s"}`];
  if (duplicates) {
    parts.push(`${duplicates} possible duplicate${duplicates === 1 ? "" : "s"}`);
  }
  if (totals) parts.push(totals);
  summary.textContent = parts.join(" · ");
}

function duplicateBadge(receipt) {
  const original = receipt.duplicate_of ? ` of ${escapeHtml(receipt.duplicate_of)}` : "";
  const hint = receipt.duplicate_of
    ? `Same merchant, date, and total as ${escapeHtml(receipt.duplicate_of)}`
    : "Same merchant, date, and total as an earlier receipt";
  return `<span class="dupe-badge" title="${hint}">Duplicate${original}</span>`;
}

function renderRows() {
  rowsBody.innerHTML = Array.from(state.receipts.values())
    .map((receipt) => {
      const confidence = Math.round((Number(receipt.confidence) || 0) * 100);
      const duplicate = Boolean(receipt.duplicate);
      return `<tr data-key="${receipt.key}"${duplicate ? ' class="row-duplicate"' : ""}>
        <td data-label="File"><span class="file-label">${escapeHtml(receipt.file)}</span>${duplicate ? duplicateBadge(receipt) : ""}</td>
        <td data-label="Merchant"><input class="cell merchant" data-field="merchant" aria-label="Merchant for ${escapeHtml(receipt.file)}" value="${escapeHtml(receipt.merchant || "")}"></td>
        <td data-label="Date"><input class="cell date" data-field="date" aria-label="Date for ${escapeHtml(receipt.file)}" value="${escapeHtml(receipt.date || "")}"></td>
        <td data-label="Total"><input class="cell total" data-field="total" aria-label="Total for ${escapeHtml(receipt.file)}" inputmode="decimal" value="${receipt.total == null ? "" : receipt.total}"></td>
        <td data-label="Tax"><input class="cell tax" data-field="tax" aria-label="Tax for ${escapeHtml(receipt.file)}" inputmode="decimal" value="${receipt.tax == null ? "" : receipt.tax}"></td>
        <td data-label="Currency"><input class="cell currency" data-field="currency" aria-label="Currency for ${escapeHtml(receipt.file)}" maxlength="3" value="${escapeHtml(receipt.currency || "")}"></td>
        <td data-label="Invoice"><input class="cell invoice" data-field="invoice_number" aria-label="Invoice number for ${escapeHtml(receipt.file)}" value="${escapeHtml(receipt.invoice_number || "")}"></td>
        <td data-label="Confidence" class="conf">${confidence}%</td>
        <td><button class="remove-row" type="button" data-key="${receipt.key}">Remove</button></td>
      </tr>`;
    })
    .join("");
  updateSummary();
}

function validate() {
  const problems = [];
  for (const row of rowsBody.querySelectorAll("tr")) {
    const total = row.querySelector('[data-field="total"]');
    const tax = row.querySelector('[data-field="tax"]');
    const date = row.querySelector('[data-field="date"]');
    for (const input of [total, tax]) {
      const valid = input.value.trim() === "" || Number.isFinite(Number(input.value));
      input.setAttribute("aria-invalid", valid ? "false" : "true");
      if (!valid) problems.push("Total and tax must be numbers.");
    }
    const dateValue = date.value.trim();
    const dateValid =
      dateValue === "" || /^\d{4}-\d{2}-\d{2}$/.test(dateValue) || /^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$/.test(dateValue);
    date.setAttribute("aria-invalid", dateValid ? "false" : "true");
    if (!dateValid) problems.push("Use YYYY-MM-DD or DD/MM/YYYY for dates.");
  }
  const unique = Array.from(new Set(problems));
  validation.textContent = unique.join(" ");
  validation.classList.toggle("is-error", unique.length > 0);
  return unique.length === 0;
}

rowsBody.addEventListener("input", () => {
  updateSummary();
  validate();
});

rowsBody.addEventListener("click", (event) => {
  const button = event.target.closest(".remove-row");
  if (!button) return;
  state.receipts.delete(button.dataset.key);
  const row = button.closest("tr");
  if (row) row.remove();
  updateSummary();
  validate();
});

function readRows() {
  return Array.from(rowsBody.querySelectorAll("tr")).map((row) => {
    const receipt = state.receipts.get(row.dataset.key) || {};
    const values = { file: receipt.file || "" };
    for (const input of row.querySelectorAll("[data-field]")) {
      values[input.dataset.field] = input.value.trim();
    }
    values.items = Array.isArray(receipt.items) ? receipt.items.length : 0;
    values.confidence = receipt.confidence || 0;
    values.warnings = Array.isArray(receipt.warnings) ? receipt.warnings.join("; ") : "";
    values.duplicate = receipt.duplicate ? "yes" : "";
    values.duplicate_of = receipt.duplicate_of || "";
    return values;
  });
}

async function scan() {
  if (!state.files.length) {
    setStatus("Add at least one receipt first.", true);
    return;
  }
  scanButton.disabled = true;
  scanButton.textContent = "Scanning...";
  setStatus("Reading receipts locally. This can take a moment.");
  result.hidden = true;
  document.querySelector("main").setAttribute("aria-busy", "true");

  const body = new FormData();
  for (const file of state.files) body.append("files", file);
  body.append("ocr", ocr.value);

  try {
    const response = await fetch("/api/scan", { method: "POST", body });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Server returned ${response.status}`);
    }
    const data = await response.json();
    state.receipts.clear();
    for (const receipt of data.receipts || []) {
      const key = crypto.randomUUID();
      state.receipts.set(key, { ...receipt, key });
    }
    result.hidden = false;
    renderRows();
    validate();
    resultTitle.focus();
    const duplicates = countDuplicates();
    setStatus(
      duplicates
        ? `Done. ${duplicates} possible duplicate${duplicates === 1 ? "" : "s"} marked. Fix any field that looks wrong, then export.`
        : "Done. Fix any field that looks wrong, then export."
    );
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    scanButton.disabled = false;
    scanButton.textContent = "Scan receipts";
    document.querySelector("main").setAttribute("aria-busy", "false");
  }
}

scanButton.addEventListener("click", scan);

document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    scan();
  }
});

function csvEscape(value) {
  let text = String(value == null ? "" : value);
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}

csvButton.addEventListener("click", () => {
  if (!validate()) return;
  const columns = [
    "file",
    "merchant",
    "date",
    "total",
    "tax",
    "currency",
    "invoice_number",
    "items",
    "confidence",
    "warnings",
    "duplicate",
    "duplicate_of",
  ];
  const rows = readRows();
  const lines = [columns.join(",")].concat(
    rows.map((row) => columns.map((column) => csvEscape(row[column])).join(","))
  );
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "expenses.csv";
  link.click();
  URL.revokeObjectURL(link.href);
});

xlsxButton.addEventListener("click", async () => {
  if (!validate()) return;
  const response = await fetch("/api/export.xlsx", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows: readRows() }),
  });
  if (!response.ok) {
    setStatus("Excel export failed. Try CSV instead.", true);
    return;
  }
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "expenses.xlsx";
  link.click();
  URL.revokeObjectURL(link.href);
});

"""Local upload and review UI."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from .export import rows_to_xlsx
from .extract import extract_file

OUTPUT_DIR = Path.home() / ".snap2sheet" / "out"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".pdf"}

app = FastAPI(title="snap2sheet", version="0.1.0")

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>snap2sheet: receipts to spreadsheet</title>
<style>
  :root { color-scheme: light dark; --ink:#17211b; --paper:#f7f5ec; --green:#1f7a4d; --line:#ddd7c6; }
  * { box-sizing:border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; background:var(--paper); color:var(--ink); }
  header { max-width:900px; margin:0 auto; padding:30px 20px 6px; }
  h1 { font-size:2rem; margin:0 0 4px; letter-spacing:-.03em; }
  .sub { color:#5d6a61; margin:0 0 18px; }
  main { max-width:900px; margin:0 auto; padding:0 20px 48px; }
  .card { background:#fff; border:1px solid var(--line); border-radius:16px; padding:18px; box-shadow:0 6px 20px rgba(20,30,24,.05); margin-bottom:16px; }
  .drop { display:block; border:2px dashed #b9b3a2; border-radius:12px; padding:24px; text-align:center; cursor:pointer; background:#fbfaf3; }
  .drop:hover { border-color:var(--green); }
  input[type=file] { display:none; }
  button { background:var(--green); color:#fff; border:0; border-radius:9px; padding:11px 16px; font-weight:700; cursor:pointer; margin:8px 6px 0 0; }
  button.secondary { background:#17211b; }
  button:disabled { opacity:.5; cursor:wait; }
  table { width:100%; border-collapse:collapse; margin-top:10px; font-size:.9rem; }
  th, td { padding:6px 5px; border-bottom:1px solid #eee7d8; text-align:left; }
  .tablewrap { overflow-x:auto; }
  table { min-width: 800px; }
  input.cell { width:100%; min-width:56px; border:1px solid #e3ddcc; border-radius:6px; padding:5px; font:inherit; font-size:.86rem; background:#fffdf7; }
  input.cell[data-field="merchant"] { min-width:170px; }
  input.cell[data-field="date"] { min-width:100px; }
  input.cell[data-field="invoice_number"] { min-width:92px; }
  .muted { color:#6c766f; font-size:.85rem; }
  .pill { display:inline-block; background:#e9f3ed; color:var(--green); border-radius:999px; padding:3px 10px; font-size:.78rem; font-weight:700; }
</style>
</head>
<body>
<header>
  <h1>snap2sheet</h1>
  <p class="sub">Point. Snap. Spreadsheet. Everything runs locally. Receipts never leave this machine.</p>
</header>
<main>
  <div class="card">
    <label class="drop" for="files">
      <strong>Choose receipt photos or PDFs</strong><br>
      <span class="muted">JPG / PNG / PDF · multiple files supported</span>
    </label>
    <input id="files" type="file" accept="image/*,application/pdf" multiple>
    <div><button id="scan" type="button">Scan</button></div>
    <div id="status" class="muted"></div>
  </div>
  <div id="out"></div>
</main>
<script>
const input = document.getElementById('files');
const scan = document.getElementById('scan');
const status = document.getElementById('status');
const out = document.getElementById('out');
let current = [];

function esc(s) { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
function cell(value, field) { return `<input class="cell" data-field="${field}" value="${esc(value)}">`; }

scan.addEventListener('click', async () => {
  if (!input.files.length) { status.textContent = 'Choose at least one file.'; return; }
  scan.disabled = true; status.textContent = 'Reading receipts locally...'; out.innerHTML = '';
  const fd = new FormData();
  for (const f of input.files) fd.append('files', f);
  try {
    const res = await fetch('/api/scan', { method: 'POST', body: fd });
    if (!res.ok) throw new Error((await res.json()).detail || 'scan failed');
    const data = await res.json();
    current = data.receipts;
    const rows = current.map((r, i) => `<tr data-i="${i}">
      <td>${esc(r.file)}</td>
      <td>${cell(r.merchant || '', 'merchant')}</td>
      <td>${cell(r.date || '', 'date')}</td>
      <td>${cell(r.total ?? '', 'total')}</td>
      <td>${cell(r.tax ?? '', 'tax')}</td>
      <td>${cell(r.currency || '', 'currency')}</td>
      <td>${cell(r.invoice_number || '', 'invoice_number')}</td>
      <td>${Math.round((r.confidence || 0) * 100)}%</td>
    </tr>`).join('');
    out.innerHTML = `<div class="card">
      <span class="pill">${current.length} receipt(s)</span>
      <h3>Review and fix anything that looks off</h3>
      <p class="muted">Then export. Corrections stay in your browser.</p>
      <div class="tablewrap"><table><thead><tr><th>File</th><th>Merchant</th><th>Date</th><th>Total</th><th>Tax</th><th>Cur</th><th>Invoice</th><th>Conf</th></tr></thead><tbody id="rows">${rows}</tbody></table></div>
      <button id="csv" type="button">Download CSV</button>
      <button id="xlsx" class="secondary" type="button">Download Excel</button>
    </div>`;
    document.getElementById('csv').onclick = downloadCsv;
    document.getElementById('xlsx').onclick = downloadXlsx;
    status.textContent = 'Done.';
  } catch (err) {
    status.innerHTML = `<span style="color:#a3261e">${esc(err.message)}</span>`;
  } finally {
    scan.disabled = false;
  }
});

function readRows() {
  return [...document.querySelectorAll('#rows tr')].map((tr, i) => {
    const base = current[i] || {};
    const row = { file: base.file || '' };
    for (const el of tr.querySelectorAll('input.cell')) row[el.dataset.field] = el.value;
    return row;
  });
}

function downloadCsv() {
  const rows = readRows();
  const cols = ['file','merchant','date','total','tax','currency','invoice_number','items','confidence','warnings'];
  const lines = [cols.join(',')].concat(rows.map(r => cols.map(c => `"${String(r[c] ?? '').replaceAll('"','""')}"`).join(',')));
  const blob = new Blob([lines.join('\\n')], { type: 'text/csv' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'expenses.csv'; a.click();
}

async function downloadXlsx() {
  const res = await fetch('/api/export.xlsx', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ rows: readRows() }) });
  if (!res.ok) { alert('Excel export failed'); return; }
  const blob = await res.blob();
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'expenses.xlsx'; a.click();
}
</script>
</body>
</html>
"""


class ExportRequest(BaseModel):
    rows: list[dict[str, object]]


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/healthz")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/scan")
async def scan(files: list[UploadFile] = File(...)) -> JSONResponse:
    receipts = []
    job = uuid.uuid4().hex
    for index, upload in enumerate(files):
        suffix = Path(upload.filename or "upload").suffix.lower()
        if suffix not in ALLOWED:
            raise HTTPException(status_code=400, detail=f"unsupported file: {upload.filename}")
        path = OUTPUT_DIR / f"{job}-{index}{suffix}"
        path.write_bytes(await upload.read())
        receipts.append(extract_file(path, source=upload.filename or path.name).to_dict())
    return JSONResponse({"receipts": receipts})


@app.post("/api/export.xlsx")
def export_xlsx(request: ExportRequest) -> FileResponse:
    name = f"{uuid.uuid4().hex}.xlsx"
    path = OUTPUT_DIR / name
    rows_to_xlsx(request.rows, path)
    return FileResponse(
        path,
        filename="expenses.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/files/{name}")
def download(name: str) -> FileResponse:
    path = OUTPUT_DIR / Path(name).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path)

"""Local upload and review UI."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

from .export import rows_to_xlsx
from .extract import extract_file
from .ocr import OCRUnavailable, backend_status

OUTPUT_DIR = Path.home() / ".snap2sheet" / "out"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATIC = Path(__file__).resolve().parent / "static"


def cleanup_old_uploads() -> None:
    """Remove receipt uploads left by older versions. Keep generated exports."""
    pattern = re.compile(r"^[0-9a-f]{32}-\d+\.[a-z0-9]+$")
    for path in OUTPUT_DIR.iterdir():
        if path.is_file() and pattern.match(path.name):
            path.unlink(missing_ok=True)


cleanup_old_uploads()
ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".pdf"}
MAX_UPLOAD = 15 * 1024 * 1024
MAX_FILES = 20

app = FastAPI(title="snap2sheet", version="0.2.2")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class ExportRequest(BaseModel):
    rows: list[dict[str, object]]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/healthz")
def health() -> dict[str, object]:
    return {"ok": True, "ocr": backend_status()}


@app.post("/api/scan")
async def scan(
    files: list[UploadFile] = File(...), ocr: str = Form("auto")
) -> JSONResponse:
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"too many files (max {MAX_FILES})")

    receipts = []
    job = uuid.uuid4().hex
    for index, upload in enumerate(files):
        suffix = Path(upload.filename or "upload").suffix.lower()
        if suffix not in ALLOWED:
            raise HTTPException(status_code=400, detail=f"unsupported file: {upload.filename}")
        payload = await upload.read(MAX_UPLOAD + 1)
        if len(payload) > MAX_UPLOAD:
            raise HTTPException(
                status_code=413, detail=f"{upload.filename}: file too large (max 15 MB)"
            )
        path = OUTPUT_DIR / f"{job}-{index}{suffix}"
        path.write_bytes(payload)
        try:
            receipt = extract_file(
                path,
                source=upload.filename or path.name,
                ocr_backend=ocr,
            )
        except OCRUnavailable as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"{upload.filename}: {exc}"
            ) from exc
        finally:
            path.unlink(missing_ok=True)
        receipts.append(receipt.to_dict())
    return JSONResponse({"receipts": receipts})


@app.post("/api/export.xlsx")
def export_xlsx(request: ExportRequest) -> FileResponse:
    if len(request.rows) > 1000:
        raise HTTPException(status_code=413, detail="too many rows (max 1000)")
    name = f"{uuid.uuid4().hex}.xlsx"
    path = OUTPUT_DIR / name
    rows_to_xlsx(request.rows, path)
    return FileResponse(
        path,
        filename="expenses.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(lambda: path.unlink(missing_ok=True)),
    )


@app.get("/files/{name}")
def download(name: str) -> FileResponse:
    path = OUTPUT_DIR / Path(name).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path)

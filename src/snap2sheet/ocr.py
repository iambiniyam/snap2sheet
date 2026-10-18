"""Image/PDF OCR with row reconstruction."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import pymupdf as fitz

from .config import indra_dir


@dataclass(frozen=True, slots=True)
class TextLine:
    text: str
    bbox: tuple[float, float, float, float]
    confidence: float = 1.0


class OCRUnavailable(RuntimeError):
    """Raised when the requested OCR backend is not installed."""


def _indra_ready() -> bool:
    try:
        import indra_ocr  # noqa: F401
    except ImportError:
        return False
    folder = indra_dir()
    return all((folder / name).exists() for name in ("det.onnx", "rec.onnx", "meta.json"))


def resolve_backend(name: str = "auto") -> str:
    name = (name or "auto").lower()
    if name == "auto":
        return "indra" if _indra_ready() else "rapidocr"
    if name in {"rapid", "rapidocr"}:
        return "rapidocr"
    if name == "indra":
        if not _indra_ready():
            raise OCRUnavailable(
                "Indra OCR is not installed or its models are missing. "
                "Run: python scripts/download_models.py --with-indra"
            )
        return "indra"
    raise ValueError(f"unknown OCR backend: {name}")


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


@lru_cache(maxsize=2)
def _indra(model_path: str, threads: int):
    import indra_ocr

    return indra_ocr.load(path=model_path, threads=threads)


def _rapid_lines(image: np.ndarray) -> list[TextLine]:
    result, _elapsed = _engine()(image)
    lines: list[TextLine] = []
    for item in result or []:
        box, text, score = item[0], item[1], float(item[2])
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        lines.append(TextLine(str(text), (min(xs), min(ys), max(xs), max(ys)), score))
    return lines


def _indra_lines(image: np.ndarray) -> list[TextLine]:
    threads = int(os.getenv("SNAP2SHEET_INDRA_THREADS", "2"))
    converter = _indra(str(indra_dir()), threads)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        path = Path(handle.name)
    try:
        if not cv2.imwrite(str(path), image):
            raise OCRUnavailable("could not prepare the image for Indra OCR")
        lines: list[TextLine] = []
        for item in converter.convert(str(path)):
            page = item[1] if isinstance(item, tuple) else item
            for line in page.lines:
                lines.append(TextLine(str(line.text), tuple(line.box), float(line.conf)))
        return lines
    finally:
        path.unlink(missing_ok=True)


def _render_pdf(path: Path, dpi: int = 200) -> np.ndarray:
    document = fitz.open(path)
    if len(document) == 0:
        raise ValueError("PDF has no pages")
    page = document[0]
    pixmap = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3)
    document.close()
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


def load_image(path: Path | str, dpi: int = 200) -> np.ndarray:
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return _render_pdf(path, dpi=dpi)
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot read image: {path}")
    return image


def backend_status() -> dict[str, object]:
    return {
        "auto": resolve_backend("auto"),
        "rapidocr": True,
        "indra": _indra_ready(),
        "indra_dir": str(indra_dir()),
    }


def ocr_lines(image: np.ndarray, backend: str = "auto") -> list[TextLine]:
    selected = resolve_backend(backend)
    lines = _indra_lines(image) if selected == "indra" else _rapid_lines(image)
    return [line for line in lines if line.text.strip() and line.confidence >= 0.5]


def group_rows(lines: list[TextLine], tolerance: float = 18.0) -> list[str]:
    """Join OCR fragments that sit on the same visual row.

    Receipt OCR often splits a description and its amount into separate boxes.
    Grouping by vertical position restores rows like `TOTAL $14.58`.
    """
    rows: list[dict[str, object]] = []
    for line in sorted(lines, key=lambda l: (l.bbox[1], l.bbox[0])):
        if rows and abs(line.bbox[1] - float(rows[-1]["y"])) <= tolerance:
            rows[-1]["lines"].append(line)  # type: ignore[union-attr]
        else:
            rows.append({"y": line.bbox[1], "lines": [line]})
    output: list[str] = []
    for row in rows:
        fragments = sorted(row["lines"], key=lambda l: l.bbox[0])  # type: ignore[arg-type]
        text = " ".join(fragment.text.strip() for fragment in fragments).strip()
        if text:
            output.append(text)
    return output


def read_text(
    path: Path | str, dpi: int = 200, backend: str = "auto"
) -> tuple[list[str], float, str]:
    """Return (rows, average OCR confidence, joined text)."""
    lines = ocr_lines(load_image(path, dpi=dpi), backend=backend)
    confidence = sum(line.confidence for line in lines) / len(lines) if lines else 0.0
    rows = group_rows(lines)
    return rows, confidence, "\n".join(rows)

"""Field-level receipt extraction benchmark for RapidOCR and Indra OCR."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from snap2sheet.extract import extract_file
from snap2sheet.ocr import OCRUnavailable

HERE = Path(__file__).resolve().parent
RECEIPTS = HERE / "receipts"
FIELDS = ("merchant", "date", "total", "tax", "currency", "invoice_number")


def score(actual, expected, field: str) -> bool:
    if field in {"total", "tax"}:
        try:
            return abs(float(actual) - float(expected)) <= 0.01
        except (TypeError, ValueError):
            return False
    if field == "merchant":
        return str(actual or "").strip().lower() == str(expected).strip().lower()
    return str(actual or "").strip() == str(expected).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backends", default="rapidocr,indra")
    args = parser.parse_args()
    truth = {row["file"]: row for row in json.loads((RECEIPTS / "ground_truth.json").read_text())}
    results = []
    for backend in [item.strip() for item in args.backends.split(",") if item.strip()]:
        correct = {field: 0 for field in FIELDS}
        started = time.perf_counter()
        rows = 0
        try:
            for name, expected in truth.items():
                path = RECEIPTS / name
                receipt = extract_file(path, source=name, ocr_backend=backend)
                rows += 1
                for field in FIELDS:
                    if score(getattr(receipt, field), expected[field], field):
                        correct[field] += 1
        except OCRUnavailable as exc:
            results.append({"backend": backend, "skipped": str(exc)})
            continue
        elapsed = round(time.perf_counter() - started, 2)
        results.append(
            {
                "backend": backend,
                "receipts": rows,
                "seconds": elapsed,
                "accuracy": {field: round(correct[field] / rows, 3) for field in FIELDS},
                "overall": round(sum(correct.values()) / (rows * len(FIELDS)), 3),
            }
        )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

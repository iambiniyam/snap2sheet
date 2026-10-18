#!/usr/bin/env python3
"""Download the optional Indra OCR models for snap2sheet."""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

from snap2sheet.config import indra_dir

BASE = "https://huggingface.co/datalab-to/indra-ocr/resolve/main"
FILES = (
    "det.onnx",
    "rec.onnx",
    "rec_cjk.onnx",
    "order.onnx",
    "orient.onnx",
    "script.onnx",
    "model.safetensors",
    "meta.json",
    "math_enc.onnx",
    "math_dec_step.onnx",
    "math_dec_init.onnx",
    "mathcls.onnx",
    "config.json",
)


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as response, temp.open("wb") as handle:
        handle.write(response.read())
    temp.replace(dest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", type=Path, default=indra_dir())
    args = parser.parse_args()

    for name in FILES:
        target = args.dest / name
        print(f"-> {BASE}/{name}")
        try:
            fetch(f"{BASE}/{name}", target)
        except Exception as exc:  # noqa: BLE001
            print(f"failed: {exc}", file=sys.stderr)
            return 1
        print(f"  saved {target} ({target.stat().st_size / 1e6:.1f} MB)")
    print("done. set SNAP2SHEET_INDRA_DIR if you used a custom folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

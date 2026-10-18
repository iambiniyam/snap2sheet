"""Paths for optional model backends."""

from __future__ import annotations

import os
from pathlib import Path


def indra_dir() -> Path:
    return Path(
        os.getenv(
            "SNAP2SHEET_INDRA_DIR",
            str(Path.home() / ".snap2sheet" / "models" / "indra"),
        )
    )

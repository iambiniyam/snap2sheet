import os
from pathlib import Path

os.environ.setdefault("SNAP2SHEET_TEST", "1")
REPO = Path(__file__).resolve().parents[1]

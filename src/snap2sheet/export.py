"""CSV and Excel export."""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import Receipt

DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: object) -> object:
    """Prevent spreadsheet formula injection without changing numbers."""
    if isinstance(value, str) and value.startswith(DANGEROUS_PREFIXES):
        return "'" + value
    return value


COLUMNS = [
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
]


PRESET_COLUMNS: dict[str, list[str]] = {
    "generic": COLUMNS,
    "quickbooks": ["Date", "Description", "Amount", "Currency", "Reference"],
    "xero": ["Date", "Amount", "Payee", "Description", "Reference", "Currency"],
}


def preset_columns(preset: str) -> list[str]:
    try:
        return PRESET_COLUMNS[preset]
    except KeyError as exc:
        raise ValueError(f"unknown preset {preset!r}; use generic, quickbooks, or xero") from exc


def _preset_row(row: dict[str, object], preset: str) -> dict[str, object]:
    if preset == "generic":
        return row
    merchant = str(row.get("merchant") or "").strip()
    invoice = str(row.get("invoice_number") or "").strip()
    description = f"{merchant} receipt" if merchant else "Receipt"
    if preset == "quickbooks":
        return {
            "Date": row.get("date", ""),
            "Description": description,
            "Amount": row.get("total", ""),
            "Currency": row.get("currency", ""),
            "Reference": invoice or row.get("file", ""),
        }
    if preset == "xero":
        return {
            "Date": row.get("date", ""),
            "Amount": row.get("total", ""),
            "Payee": merchant,
            "Description": description,
            "Reference": invoice or row.get("file", ""),
            "Currency": row.get("currency", ""),
        }
    raise ValueError(f"unknown preset {preset!r}")


def write_csv(receipts: list[Receipt], path: Path | str, preset: str = "generic") -> Path:
    columns = preset_columns(preset)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for receipt in receipts:
            row = _preset_row(receipt.to_row(), preset)
            writer.writerow({key: safe_cell(row.get(key, "")) for key in columns})
    return path


def rows_to_xlsx(rows: list[dict[str, object]], path: Path | str, preset: str = "generic") -> Path:
    columns = preset_columns(preset)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "expenses"
    sheet.append(columns)
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F7A4D")
    for cell in sheet[1]:
        cell.font = header_font
        cell.fill = header_fill
    for row in rows:
        preset_row = _preset_row(row, preset)
        sheet.append([safe_cell(preset_row.get(column, "")) for column in columns])
    widths = {"file": 28, "merchant": 30, "date": 12, "total": 10, "tax": 10,
              "currency": 9, "invoice_number": 16, "items": 7, "confidence": 11,
              "warnings": 45, "duplicate": 11, "duplicate_of": 28}
    for index, column in enumerate(columns, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = widths.get(column, 14)
    sheet.freeze_panes = "A2"
    workbook.save(path)
    return path


def write_xlsx(receipts: list[Receipt], path: Path | str, preset: str = "generic") -> Path:
    return rows_to_xlsx([receipt.to_row() for receipt in receipts], path, preset=preset)

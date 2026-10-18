"""Receipt/invoice field extraction from OCR rows."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .models import Receipt
from .ocr import read_text

MONEY = re.compile(
    r"(?:(?P<code>USD|EUR|GBP|KES|NGN|GHS|ETB|ZAR|INR|CAD|AUD)\s*)?"
    r"(?P<symbol>[$€£¥₹]\s*)?"
    r"(?P<number>-?\d{1,3}(?:[,\s]\d{3})+(?:[.,]\d{2})?|-?\d+[.,]\d{2})",
    re.IGNORECASE,
)

TOTAL = re.compile(r"\b(grand\s+total|total\s+due|amount\s+due|balance\s+due|total)\b", re.I)
EXCLUDE_TOTAL = re.compile(r"\b(subtotal|sub-total|tax|vat|gst|hst|discount|items|qty)\b", re.I)
TAX = re.compile(r"\b(vat|tax|gst|hst|sales\s+tax)\b", re.I)
INVOICE = re.compile(
    r"\b(?:invoice|inv|receipt|bill|order)\s*(?:#|no\.?|number|id)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})",
    re.I,
)
ITEM = re.compile(r"^(?P<desc>.+?)\s+(?P<amount>-?\d+[.,]\d{2})\s*$")
QUANTITY = re.compile(r"^(?P<qty>\d+)\s*[xX\u00d7]\s*(?P<rest>.+)$")

SKIP_MERCHANT = re.compile(
    r"(receipt|invoice|tax\s+invoice|tel|phone|www|http|thank|welcome|date|"
    r"cash|visa|mastercard|amex|card|change|subtotal|total|tax|vat|gst|"
    r"address|street|road|avenue|ave\.?|suite|floor|box|order\s*#)",
    re.I,
)

SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR"}
CODES = ("USD", "EUR", "GBP", "KES", "NGN", "GHS", "ETB", "ZAR", "INR", "CAD", "AUD")


def parse_amount(raw: str) -> float:
    """Parse `1,234.56`, `1.234,56`, `$14.58`, or `9.00`."""
    value = raw.strip().replace(" ", "")
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        if len(value.rsplit(",", 1)[-1]) == 2:
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "." in value:
        if len(value.rsplit(".", 1)[-1]) != 2:
            value = value.replace(".", "")
    return float(value)


def find_amount(row: str) -> tuple[float | None, str | None]:
    """Return the last amount on a row and any explicit currency."""
    amounts = list(MONEY.finditer(row))
    if not amounts:
        return None, None
    match = amounts[-1]
    try:
        amount = parse_amount(match.group("number"))
    except ValueError:
        return None, None
    currency = (match.group("code") or "").upper() or None
    if currency is None and match.group("symbol"):
        currency = SYMBOLS.get(match.group("symbol").strip())
    return amount, currency


def parse_date(text: str, order: str = "mdy") -> str | None:
    match = re.search(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", text)
    if match:
        year, month, day = (int(part) for part in match.groups())
        return _iso(year, month, day)

    match = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\b", text)
    if match:
        first, second = int(match.group(1)), int(match.group(2))
        year = int(match.group(3))
        year = year + 2000 if year < 100 and year <= 69 else (year + 1900 if year < 100 else year)
        if order == "dmy":
            day, month = first, second
        else:
            month, day = first, second
        if month > 12 and day <= 12:
            month, day = day, month
        return _iso(year, month, day)

    for fmt in ("%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _iso(year: int, month: int, day: int) -> str | None:
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def _merchant(rows: list[str]) -> str | None:
    for row in rows[: max(4, len(rows) // 3)]:
        text = row.strip(" -|")
        if len(text) < 3 or SKIP_MERCHANT.search(text):
            continue
        letters = sum(char.isalpha() for char in text)
        if letters >= 3 and letters / max(1, len(text)) >= 0.45:
            return text
    return None


def _total(rows: list[str]) -> tuple[float | None, str | None]:
    for row in reversed(rows):
        if TOTAL.search(row) and not EXCLUDE_TOTAL.search(row):
            amount, currency = find_amount(row)
            if amount is not None:
                return amount, currency
    # Fallback: the largest amount in the bottom half, with a warning.
    candidates = [find_amount(row) for row in rows[len(rows) // 2 :]]
    amounts = [(amount, currency) for amount, currency in candidates if amount is not None]
    if amounts:
        return max(amounts, key=lambda pair: pair[0])
    return None, None


def _tax(rows: list[str]) -> float | None:
    for row in rows:
        if TAX.search(row) and not re.search(r"tax\s+invoice", row, re.I):
            amount, _currency = find_amount(row)
            if amount is not None:
                return amount
    return None


def _invoice(rows: list[str]) -> str | None:
    for row in rows:
        match = INVOICE.search(row)
        if not match:
            continue
        value = match.group(1).strip(" :-")
        if re.fullmatch(r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}", value):
            continue
        if len(value) >= 3 and any(char.isdigit() for char in value):
            return value
    return None


def _currency(rows: list[str], explicit: str | None) -> tuple[str | None, list[str]]:
    warnings: list[str] = []
    if explicit:
        return explicit, warnings
    text = " ".join(rows).upper()
    for code in CODES:
        if re.search(rf"\b{code}\b", text):
            return code, warnings
    for symbol, code in SYMBOLS.items():
        if symbol in text:
            if symbol == "$":
                warnings.append("currency assumed USD from '$'. Verify.")
            return code, warnings
    return None, warnings


def _items(rows: list[str]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for row in rows:
        if TOTAL.search(row) or TAX.search(row) or re.search(r"subtotal|change|cash|visa|mastercard", row, re.I):
            continue
        match = ITEM.match(row)
        if not match:
            continue
        description = match.group("desc").strip()
        if sum(char.isalpha() for char in description) < 2:
            continue
        try:
            amount = parse_amount(match.group("amount"))
        except ValueError:
            continue
        quantity = 1
        quantity_match = QUANTITY.match(description)
        if quantity_match:
            quantity = int(quantity_match.group("qty")) or 1
            description = quantity_match.group("rest").strip()
        items.append(
            {
                "description": description,
                "quantity": quantity,
                "amount": round(amount, 2),
                "unit_price": round(amount / quantity, 2) if quantity else None,
            }
        )
    return items


def extract_receipt(
    source: str, rows: list[str], ocr_confidence: float = 1.0, order: str = "mdy"
) -> Receipt:
    text = "\n".join(rows)
    merchant = _merchant(rows)
    total, total_currency = _total(rows)
    tax = _tax(rows)
    currency, warnings = _currency(rows, total_currency)
    invoice_number = _invoice(rows)
    date = parse_date(text, order=order)

    receipt = Receipt(
        source=source,
        merchant=merchant,
        date=date,
        total=total,
        tax=tax,
        currency=currency,
        invoice_number=invoice_number,
        items=_items(rows),
        raw_text=text,
        warnings=warnings,
    )

    score = 0.15
    score += 0.20 if merchant else 0.0
    score += 0.20 if date else 0.0
    score += 0.30 if total is not None else 0.0
    score += 0.05 if tax is not None else 0.0
    score += 0.05 if currency else 0.0
    score += 0.05 if invoice_number else 0.0
    if not merchant:
        receipt.warnings.append("merchant not found")
    if date is None:
        receipt.warnings.append("date not found")
    if total is None:
        receipt.warnings.append("total not found. Check manually.")
    if ocr_confidence < 0.85:
        score -= 0.10
        receipt.warnings.append(f"low OCR confidence ({ocr_confidence:.2f})")
    receipt.confidence = round(max(0.0, min(0.95, score)), 2)
    return receipt


def extract_file(path: Path | str, order: str = "mdy", source: str | None = None) -> Receipt:
    rows, confidence, _text = read_text(path)
    return extract_receipt(source or Path(path).name, rows, confidence, order=order)

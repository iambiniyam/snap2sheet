"""Conservative duplicate detection for a batch of receipts.

The key uses the three fields a person would compare by hand: merchant, date,
and total. All three must normalize successfully. When a field is missing,
invalid, or ambiguous we return no key, so a partial match can never turn into
a false duplicate warning.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .models import Receipt

DATE_FORMATS = (
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d-%b-%Y",
)
YEAR_FIRST = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
MERCHANT_NOISE = re.compile(r"[\W_]+", re.UNICODE)


def normalize_merchant(merchant: str | None) -> str | None:
    """Case-fold a merchant and collapse punctuation and whitespace."""
    if merchant is None:
        return None
    text = unicodedata.normalize("NFKC", str(merchant)).casefold()
    text = " ".join(MERCHANT_NOISE.sub(" ", text).split())
    return text or None


def normalize_date(value: str | date | None) -> str | None:
    """Return an ISO date, or None when the value is missing or ambiguous.

    Year-first dates and unambiguous month-name formats are accepted. Numeric
    ``DD/MM/YYYY`` and ``MM/DD/YYYY`` values are refused because the order is
    not knowable in this module; guessing could merge two different receipts.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None

    match = YEAR_FIRST.fullmatch(text)
    if match:
        year, month, day = (int(part) for part in match.groups())
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_total(total: float | str | None) -> str | None:
    """Return a two-decimal string, or None for a missing or invalid total."""
    if total is None or isinstance(total, bool):
        return None
    text = str(total).strip().replace(" ", "")
    if not text or "," in text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    if not value.is_finite():
        return None
    try:
        value = value.quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    return f"{value:.2f}"


def duplicate_key(receipt: Receipt) -> str | None:
    """Return a deterministic identity key, or None if any field is unusable."""
    merchant = normalize_merchant(receipt.merchant)
    day = normalize_date(receipt.date)
    total = normalize_total(receipt.total)
    if merchant is None or day is None or total is None:
        return None
    return f"{merchant}|{day}|{total}"


def annotate_duplicates(receipts: Iterable[Receipt]) -> list[Receipt]:
    """Recompute ``duplicate`` and ``duplicate_of`` for a whole batch.

    The first receipt with a given key is the original. Later receipts with the
    same key are marked but still returned: callers keep every row. Receipts
    without a complete key are always left unmarked.
    """
    batch = list(receipts)
    originals: dict[str, str] = {}
    for index, receipt in enumerate(batch, start=1):
        receipt.duplicate = False
        receipt.duplicate_of = None
        key = duplicate_key(receipt)
        if key is None:
            continue
        original = originals.get(key)
        if original is None:
            originals[key] = receipt.source or f"receipt {index}"
            continue
        receipt.duplicate = True
        receipt.duplicate_of = original
    return batch


def count_duplicates(receipts: Iterable[Receipt]) -> int:
    """Count receipts already marked by :func:`annotate_duplicates`."""
    return sum(1 for receipt in receipts if receipt.duplicate)

"""Structured receipt output."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Receipt:
    source: str
    merchant: str | None = None
    date: str | None = None
    total: float | None = None
    tax: float | None = None
    currency: str | None = None
    invoice_number: str | None = None
    items: list[dict[str, object]] = field(default_factory=list)
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)
    raw_text: str = field(default="", repr=False)

    def to_row(self) -> dict[str, object]:
        return {
            "file": self.source,
            "merchant": self.merchant or "",
            "date": self.date or "",
            "total": f"{self.total:.2f}" if self.total is not None else "",
            "tax": f"{self.tax:.2f}" if self.tax is not None else "",
            "currency": self.currency or "",
            "invoice_number": self.invoice_number or "",
            "items": len(self.items),
            "confidence": f"{self.confidence:.2f}",
            "warnings": "; ".join(self.warnings),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "file": self.source,
            "merchant": self.merchant,
            "date": self.date,
            "total": self.total,
            "tax": self.tax,
            "currency": self.currency,
            "invoice_number": self.invoice_number,
            "items": self.items,
            "confidence": round(self.confidence, 3),
            "warnings": self.warnings,
        }

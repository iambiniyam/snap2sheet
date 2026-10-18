"""Optional LLM refinement for messy receipts.

Uses any OpenAI-compatible endpoint. Heuristics remain the default so the tool
works offline; the LLM is opt-in per run.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import httpx

from .models import Receipt


@dataclass(slots=True)
class LLMSettings:
    base_url: str
    api_key: str
    model: str
    timeout: float = 45.0

    @classmethod
    def from_env(cls) -> "LLMSettings":
        return cls(
            base_url=os.getenv("SNAP2SHEET_LLM_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            api_key=os.getenv("SNAP2SHEET_LLM_API_KEY", ""),
            model=os.getenv("SNAP2SHEET_LLM_MODEL", "deepseek-chat"),
        )

    @property
    def ready(self) -> bool:
        return bool(self.api_key)


PROMPT = """Extract receipt or invoice fields from the OCR text below.
Return ONLY JSON with these keys:
merchant (string or null), date (YYYY-MM-DD or null), total (number or null),
tax (number or null), currency (ISO code or null), invoice_number (string or null).
Rules: use the final total, not subtotal; do not invent values; numbers must be plain JSON numbers.
"""


def extract_with_llm(text: str, settings: LLMSettings) -> dict[str, object]:
    if not settings.ready:
        raise RuntimeError("SNAP2SHEET_LLM_API_KEY is not set")
    payload = {
        "model": settings.model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": text[:6000]},
        ],
    }
    with httpx.Client(timeout=settings.timeout) as client:
        response = client.post(
            f"{settings.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.api_key}"},
            json=payload,
        )
    if response.status_code >= 400:
        raise RuntimeError(f"LLM HTTP {response.status_code}: {response.text[:200]}")
    content = response.json()["choices"][0]["message"]["content"]
    content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("LLM did not return a JSON object")
    return data


def refine(receipt: Receipt, settings: LLMSettings) -> Receipt:
    """Let the LLM fill or correct fields; heuristics win on failure."""
    try:
        data = extract_with_llm(receipt.raw_text, settings)
    except Exception as exc:  # noqa: BLE001 - refinement is best-effort
        receipt.warnings.append(f"LLM refinement skipped: {exc}")
        return receipt

    for key in ("merchant", "date", "currency", "invoice_number"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            setattr(receipt, key, value.strip())
    for key in ("total", "tax"):
        value = data.get(key)
        if isinstance(value, (int, float)):
            setattr(receipt, key, round(float(value), 2))
    receipt.warnings.append("fields refined by LLM — verify")
    return receipt

"""Generate varied synthetic receipts with ground truth for the extraction benchmark."""

from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "receipts"
MERCHANTS = [
    ("BLUE BOTTLE COFFEE", "123 Market Street", "USD", "$"),
    ("GREEN LEAF GROCERY", "48 Oak Avenue", "USD", "$"),
    ("CAFE MILANO", "9 Via Roma", "EUR", "€"),
    ("THE CORNER BAKERY", "17 High Road", "GBP", "£"),
    ("SUNRISE PHARMACY", "220 Lakeview Drive", "USD", "$"),
    ("HARVEST TABLE", "5 Market Square", "EUR", "€"),
]
ITEMS = [
    ("Latte", 4.50),
    ("Croissant", 3.25),
    ("Sandwich", 8.90),
    ("Orange juice", 4.10),
    ("Coffee beans", 12.00),
    ("Soap", 3.75),
]


def make_receipt(index: int, rng: random.Random) -> dict:
    merchant, address, currency, symbol = rng.choice(MERCHANTS)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    year = 2026
    items = rng.sample(ITEMS, k=rng.randint(2, 3))
    subtotal = round(sum(price for _, price in items), 2)
    tax = round(subtotal * rng.choice([0.05, 0.08, 0.10]), 2)
    total = round(subtotal + tax, 2)
    due_label = rng.choice(["TOTAL", "TOTAL DUE", "AMOUNT DUE"])
    tax_label = rng.choice([f"Tax ({int(tax / subtotal * 100)}%)", "VAT", "SALES TAX"])
    receipt_no = f"{rng.randint(1000, 9999)}"

    width, height = 900, 1150
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font_path = None
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(candidate).exists():
            font_path = candidate
            break
    if font_path:
        title_font = ImageFont.truetype(font_path, 34)
        font = ImageFont.truetype(font_path, 26)
    else:
        title_font = ImageFont.load_default(size=34)
        font = ImageFont.load_default(size=26)
    y = 50

    draw.text((60, y), merchant, fill="black", font=title_font)
    y += 70
    draw.text((60, y), address, fill="black", font=font)
    y += 50
    draw.text((60, y), "Tel: (555) 123-4567", fill="black", font=font)
    y += 70
    draw.text((60, y), f"Date: {month:02d}/{day:02d}/{year}", fill="black", font=font)
    y += 50
    draw.text((60, y), f"Receipt #: {receipt_no}", fill="black", font=font)
    y += 70

    for name, price in items:
        draw.text((60, y), f"1 x {name}", fill="black", font=font)
        draw.text((650, y), f"{price:.2f}", fill="black", font=font)
        y += 50

    y += 20
    draw.text((60, y), "Subtotal", fill="black", font=font)
    draw.text((650, y), f"{subtotal:.2f}", fill="black", font=font)
    y += 50
    draw.text((60, y), tax_label, fill="black", font=font)
    draw.text((650, y), f"{tax:.2f}", fill="black", font=font)
    y += 50
    draw.text((60, y), due_label, fill="black", font=font)
    draw.text((620, y), f"{symbol}{total:.2f}", fill="black", font=font)
    y += 80
    draw.text((60, y), "Thank you!", fill="black", font=font)

    path = OUT / f"receipt_{index:02d}.png"
    image.save(path)
    return {
        "file": path.name,
        "merchant": merchant,
        "date": f"{year}-{month:02d}-{day:02d}",
        "total": total,
        "tax": tax,
        "currency": currency,
        "invoice_number": receipt_no,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    rows = [make_receipt(index, rng) for index in range(1, 13)]
    (OUT / "ground_truth.json").write_text(json.dumps(rows, indent=2))
    print(f"wrote {len(rows)} receipts to {OUT}")


if __name__ == "__main__":
    main()

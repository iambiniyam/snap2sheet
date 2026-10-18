from pathlib import Path

from snap2sheet.extract import extract_file, parse_amount, parse_date
from snap2sheet.ocr import group_rows, TextLine

FIXTURE = Path(__file__).parent / "fixtures" / "receipt.png"


def test_parse_amount():
    assert parse_amount("14.58") == 14.58
    assert parse_amount("1,234.56") == 1234.56
    assert parse_amount("1.234,56") == 1234.56
    assert parse_amount("1 234,56") == 1234.56


def test_parse_date_mdy():
    assert parse_date("Date:12/03/2026", order="mdy") == "2026-12-03"


def test_parse_date_dmy():
    assert parse_date("Date:12/03/2026", order="dmy") == "2026-03-12"


def test_parse_date_iso():
    assert parse_date("2026-03-12") == "2026-03-12"


def test_group_rows():
    lines = [
        TextLine("TOTAL", (10, 100, 80, 120)),
        TextLine("$14.58", (300, 102, 380, 122)),
        TextLine("BLUE BOTTLE", (10, 20, 200, 40)),
    ]
    assert group_rows(lines) == ["BLUE BOTTLE", "TOTAL $14.58"]


def test_extract_fixture():
    receipt = extract_file(FIXTURE)
    assert receipt.merchant == "BLUE BOTTLE COFFEE"
    assert receipt.date == "2026-12-03"
    assert receipt.total == 14.58
    assert receipt.tax == 1.08
    assert receipt.currency == "USD"
    assert receipt.invoice_number == "004512"
    assert len(receipt.items) == 2
    assert receipt.items[0]["description"] == "Latte"
    assert receipt.items[0]["quantity"] == 2

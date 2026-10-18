import csv

from openpyxl import load_workbook

from snap2sheet.export import write_csv, write_xlsx
from snap2sheet.models import Receipt


def _receipt():
    return Receipt(
        source="receipt.png",
        merchant="Blue Bottle",
        date="2026-12-03",
        total=14.58,
        tax=1.08,
        currency="USD",
        invoice_number="004512",
        confidence=0.95,
    )


def test_csv(tmp_path):
    path = write_csv([_receipt()], tmp_path / "out.csv")
    rows = list(csv.DictReader(path.open()))
    assert rows[0]["merchant"] == "Blue Bottle"
    assert rows[0]["total"] == "14.58"


def test_xlsx(tmp_path):
    path = write_xlsx([_receipt()], tmp_path / "out.xlsx")
    sheet = load_workbook(path).active
    assert sheet["A1"].value == "file"
    assert sheet["B2"].value == "Blue Bottle"
    assert sheet["D2"].value == "14.58"

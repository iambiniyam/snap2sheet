from openpyxl import load_workbook

from snap2sheet.export import rows_to_xlsx, safe_cell, write_csv
from snap2sheet.models import Receipt


def test_safe_cell_blocks_formulas():
    assert safe_cell("=HYPERLINK(\"http://x\")").startswith("'=")
    assert safe_cell("+1") == "'+1"
    assert safe_cell("-1") == "'-1"
    assert safe_cell(14.58) == 14.58


def test_xlsx_cells_are_not_formulas(tmp_path):
    path = rows_to_xlsx(
        [{"merchant": "=HYPERLINK(\"http://x\")", "total": "10.00"}],
        tmp_path / "out.xlsx",
    )
    sheet = load_workbook(path, data_only=False).active
    merchant = sheet.cell(row=2, column=2).value
    assert merchant.startswith("'=")
    assert sheet.cell(row=2, column=1).value in (None, "")


def test_csv_cells_are_not_formulas(tmp_path):
    receipt = Receipt(source="r.png", merchant="=cmd|' /C calc'!A0")
    path = write_csv([receipt], tmp_path / "out.csv")
    text = path.read_text()
    assert "'=cmd" in text
    assert "\n=cmd" not in text


def test_accounting_presets(tmp_path):
    receipt = Receipt(
        source="r.png",
        merchant="Blue Bottle",
        date="2026-03-12",
        total=14.58,
        currency="USD",
        invoice_number="004512",
    )
    quickbooks = write_csv([receipt], tmp_path / "quickbooks.csv", preset="quickbooks")
    assert quickbooks.read_text().splitlines()[0] == "Date,Description,Amount,Currency,Reference"
    assert "Blue Bottle receipt" in quickbooks.read_text()

    xero = write_csv([receipt], tmp_path / "xero.csv", preset="xero")
    assert xero.read_text().splitlines()[0] == "Date,Amount,Payee,Description,Reference,Currency"
    assert "Blue Bottle" in xero.read_text()

    sheet = load_workbook(rows_to_xlsx([receipt.to_row()], tmp_path / "xero.xlsx", preset="xero")).active
    assert [cell.value for cell in sheet[1]] == ["Date", "Amount", "Payee", "Description", "Reference", "Currency"]

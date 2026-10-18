# snap2sheet

[![ci](https://github.com/iambiniyam/snap2sheet/actions/workflows/ci.yml/badge.svg)](https://github.com/iambiniyam/snap2sheet/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Turn receipt photos into a spreadsheet.

Photograph a receipt or invoice. snap2sheet extracts the merchant, date, total, tax, currency, invoice number, and line items. Then it exports a CSV or Excel file. Everything runs locally.

![snap2sheet web UI](docs/demo.png)

Status: v0.2.1. RapidOCR is the default fallback. Indra OCR is optional, faster, and more accurate on merchant text. Review the rows before you file them.

## Why

Freelancers, small shops, and families all end up with a pile of receipts. Most expense apps upload every photo and charge a monthly fee. snap2sheet reads the receipt on your machine and gives you a file you own.

It also runs in batch. Point it at a folder and you get one spreadsheet instead of twenty manual entries.

## What is new in 0.2.0

- Rebuilt the web interface with multi-file drag and drop, editable review, validation, CSV export, and Excel export.
- Added automatic dark mode, keyboard access, loading states, error recovery, and mobile layouts.
- Added optional Indra OCR alongside RapidOCR.
- Added a subtotal and tax consistency check that fixes corrupted totals.
- Added a 12-receipt field extraction benchmark.
- Labelled every review field for screen readers.

## What it extracts

| Field | Method |
|---|---|
| Merchant | top-of-receipt text, filtered to skip addresses, phone numbers, and receipt labels |
| Date | ISO dates, DD/MM/YYYY, MM/DD/YYYY, and month names. Choose `mdy` or `dmy` order. |
| Total | rows containing TOTAL, but not subtotal or tax. Falls back to subtotal plus tax when the OCR total is implausible. |
| Tax | TAX, VAT, GST, and HST rows |
| Currency | ISO codes and the symbols $, EUR, GBP, JPY, and INR |
| Invoice number | Receipt #, Invoice No, Bill #, and Order # |
| Line items | description and amount rows, with quantity parsing |
| Confidence and warnings | missing fields, low OCR confidence, inferred currency, corrected totals |

## Quickstart

```bash
git clone https://github.com/iambiniyam/snap2sheet.git
cd snap2sheet
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
snap2sheet scan tests/fixtures/receipt.png
snap2sheet batch ./receipts -o expenses.csv --xlsx expenses.xlsx
snap2sheet serve
```

For the optional Indra backend:

```bash
uv pip install -e ".[indra]"
python scripts/download_models.py
snap2sheet scan receipt.jpg --ocr indra
```

`auto` uses Indra when its models are installed, and RapidOCR otherwise.

## OCR benchmark

Twelve generated receipts with known fields. See [docs/evaluation.md](docs/evaluation.md).

| Backend | Merchant | Total | Currency | Overall | Time |
|---|---|---|---|---|---|
| RapidOCR | 0.167 | 1.000 | 0.333 | 0.750 | 16.1 s |
| Indra OCR | 1.000 | 1.000 | 0.333 | 0.889 | 4.0 s |

Indra reads merchant titles correctly and is faster. Both backends miss euro and pound symbols on some receipts, which is why currency stays editable in the review screen.

## CLI

```bash
# one receipt
snap2sheet scan receipt.jpg

# a folder, with day-first dates
snap2sheet batch ./receipts -o expenses.csv --xlsx expenses.xlsx --order dmy

# choose the OCR engine
snap2sheet batch ./receipts -o expenses.csv --ocr indra

# optional LLM refinement for crumpled or unusual receipts
export SNAP2SHEET_LLM_BASE_URL=https://api.deepseek.com
export SNAP2SHEET_LLM_MODEL=deepseek-chat
export SNAP2SHEET_LLM_API_KEY=...
snap2sheet batch ./receipts -o expenses.csv --llm
```

## Web UI

`snap2sheet serve` opens a local review page with:

- drag and drop, file picker, and paste support for multiple receipts
- an OCR engine choice
- an editable table for merchant, date, total, tax, currency, and invoice number
- inline validation for numbers and dates
- a running total per currency
- CSV and Excel export
- loading, empty, and error states
- automatic dark mode and reduced-motion support
- keyboard access and visible focus

The page has no external fonts, scripts, or CDNs.

## How it works

```
photo or PDF
  |
  v
render at 200 DPI
  |
  v
RapidOCR or Indra OCR
  |
  v
group lines by vertical position
  |
  +--> merchant and date
  +--> total, subtotal, and tax
  +--> line items
  |
  v
CSV or XLSX
```

Row grouping is the important part. Receipt OCR often splits `TOTAL` and `$14.58` into separate boxes. Grouping by vertical position puts them back on the same row.

The subtotal correction compares subtotal plus tax with the OCR total. If the total is off by more than 50 percent, the computed value replaces it. This fixes cases where a currency symbol is misread as a leading digit.

The default path is fully offline and deterministic. The optional LLM pass can rewrite fields, but it never invents a missing receipt.

## Accuracy and limits

The benchmark uses clean, generated receipts. Real receipts are harder:

- crumpled, faded, thermal paper, or skewed photos
- handwritten totals and tips
- multiple currencies and tax-inclusive totals
- invoices that span several pages (only the first page is read today)
- ambiguous dates such as 03/04/2026, which need `--order mdy` or `dmy`

Euro and pound symbols can be misread. The currency field is editable for that reason. Low-confidence rows are flagged. Review them before filing.

## Privacy

- No network calls in the default path.
- The web UI writes uploads to `~/.snap2sheet/out`. Delete them at any time.
- The optional LLM pass sends OCR text only, never the image.

## Tests

```bash
pytest -q
```

The suite has 8 tests covering amount parsing, date order, row grouping, extraction, CSV, and Excel.

## Roadmap

- duplicate receipt detection across batches
- multi-page invoices
- tip and discount handling
- category suggestions from line items
- QuickBooks and Xero CSV presets
- a mobile-friendly PWA
- a local vision model for currency symbols and handwriting

## Related tools

- [redact](https://github.com/iambiniyam/redact): offline PII redaction for PDFs and photos.
- [find-local](https://github.com/iambiniyam/find-local): offline semantic search for files, PDFs, and photos.
- [shamba](https://github.com/iambiniyam/shamba): offline plant health scanner for gardeners and farmers.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [THIRD_PARTY.md](THIRD_PARTY.md) for the OCR and PDF dependencies.

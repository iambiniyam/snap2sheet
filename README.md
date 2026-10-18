# snap2sheet

**Point. Snap. Spreadsheet.**

Photograph a receipt or invoice. Get a clean row: merchant, date, total, tax, currency, invoice number, and line items — exported to CSV or Excel. Everything runs on your machine; receipts never leave it.

> Status: early MVP. Heuristics on top of OCR, with an optional LLM pass for messy receipts. Review before you file.

![snap2sheet web UI](docs/demo.png)

## Why

Expense tracking is tedious everywhere: freelancers, small shops, NGOs, families. The dominant apps are cloud subscriptions that upload every receipt. `snap2sheet` is the opposite:

- **Offline** — OCR and extraction run locally.
- **Batch** — point it at a folder, get one spreadsheet.
- **Reviewable** — edit any field before exporting.
- **Portable** — CSV and Excel, no lock-in.

## What it extracts

| Field | How |
|---|---|
| Merchant | top-of-receipt text, filtering addresses/phone/receipt labels |
| Date | ISO, `DD/MM/YYYY`, `MM/DD/YYYY`, month names (choose `mdy` or `dmy`) |
| Total | rows containing `TOTAL` (not subtotal/tax), fallback to largest amount |
| Tax | `TAX`, `VAT`, `GST`, `HST` rows |
| Currency | ISO codes and `$ € £ ¥ ₹` symbols |
| Invoice number | `Receipt #`, `Invoice No`, `Bill #`, `Order #` |
| Line items | description + amount rows (with quantity parsing) |
| Confidence + warnings | missing fields, low OCR confidence, inferred currency |

## Quickstart

```bash
git clone https://github.com/iambiniyam/snap2sheet.git
cd snap2sheet
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
snap2sheet scan tests/fixtures/receipt.png
snap2sheet batch ./receipts -o expenses.csv --xlsx expenses.xlsx
snap2sheet serve            # http://127.0.0.1:8789
```

## CLI

```bash
# one receipt
snap2sheet scan receipt.jpg

# a folder, with European date order
snap2sheet batch ./receipts -o expenses.csv --xlsx expenses.xlsx --order dmy

# optional LLM refinement for crumpled or unusual receipts
export SNAP2SHEET_LLM_BASE_URL=https://api.deepseek.com
export SNAP2SHEET_LLM_MODEL=deepseek-chat
export SNAP2SHEET_LLM_API_KEY=...
snap2sheet batch ./receipts -o expenses.csv --llm
```

Example:

```
        snap2sheet · 1 receipt(s)
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━┳━━━━━━┓
┃ File        ┃ Merchant          ┃ Date       ┃ Total ┃ Tax  ┃ Cur ┃ Conf ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━╇━━━━━━┩
│ receipt.png │ BLUE BOTTLE COFFEE│ 2026-12-03 │ 14.58 │ 1.08 │ USD │ 0.95 │
└─────────────┴───────────────────┴────────────┴───────┴──────┴─────┴──────┘
```

## Web UI

`snap2sheet serve` opens a multi-file upload page. Every field is editable, then download CSV or Excel. Corrections stay in the browser until you export.

## How it works

```
photo/PDF ─► render 200 DPI ─► RapidOCR ─► group rows by vertical position
                                              │
                          ┌───────────────────┼───────────────────┐
                          ▼                   ▼                   ▼
                    merchant/date        total/tax           line items
                          │                   │                   │
                          └──────────► Receipt ──────────► CSV / XLSX
                                              │
                                     optional LLM refinement
```

- **Row grouping** matters: receipt OCR often splits `TOTAL` and `$14.58` into separate boxes.
- **Heuristics first**, so the default path is fully offline and deterministic.
- **Optional LLM** (any OpenAI-compatible endpoint) only rewrites fields; it never invents a missing receipt.

## Accuracy and limits

Tested on clean, synthetic receipts (see `tests/`). Real-world receipts are harder:

- crumpled, faded, thermal paper, skewed photos;
- handwritten totals and tips;
- multi-currency receipts and tax-inclusive totals;
- invoices spanning several pages (only the first page is read today);
- ambiguous dates (`03/04/2026`) — pick `--order mdy` or `dmy`.

Low-confidence extractions are flagged; always review before filing.

## Privacy

- No network calls in the default path.
- The web UI writes uploads to `~/.snap2sheet/out`; delete them anytime.
- The optional LLM pass sends only OCR text, never the image.

## Roadmap

- [ ] Duplicate-receipt detection across batches
- [ ] Multi-page invoices
- [ ] Tip and discount handling
- [ ] Category suggestions from line items
- [ ] QuickBooks / Xero CSV presets
- [ ] Mobile-friendly PWA
- [ ] Public benchmark of field-level accuracy on real receipts

## License

MIT.

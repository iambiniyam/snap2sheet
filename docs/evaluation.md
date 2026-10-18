# Receipt extraction evaluation

This measures field-level extraction on 12 generated receipts with known values. It compares RapidOCR and Indra OCR.

## Fixture

`benchmarks/generate_receipts.py` creates receipts with:

- six merchants across USD, EUR, and GBP
- random dates, totals, and tax rates
- `TOTAL`, `TOTAL DUE`, and `AMOUNT DUE` labels
- `Tax (8%)`, `VAT`, and `SALES TAX` labels
- random receipt numbers and item lines

Ground truth is written to `benchmarks/receipts/ground_truth.json`. The images are generated locally and are not committed.

## Method

1. Generate the receipts.
2. Run `extract_file` on each image with each OCR backend.
3. Compare six fields: merchant, date, total, tax, currency, invoice number.
4. Totals and tax allow a 0.01 difference. Merchant comparison ignores case.
5. Report per-field accuracy and overall accuracy.

Commands:

```bash
python benchmarks/generate_receipts.py
SNAP2SHEET_INDRA_DIR=/path/to/indra python benchmarks/bench_extraction.py
```

## Results

| Backend | Merchant | Date | Total | Tax | Currency | Invoice | Overall | Time |
|---|---|---|---|---|---|---|---|---|
| RapidOCR | 0.167 | 1.000 | 1.000 | 1.000 | 0.333 | 1.000 | 0.750 | 16.1 s |
| Indra OCR | 1.000 | 1.000 | 1.000 | 1.000 | 0.333 | 1.000 | 0.889 | 4.0 s |

Indra reads the merchant title correctly and is about four times faster. Both backends read dates, totals, tax, and invoice numbers correctly after the subtotal correction.

## Currency failures

Both backends miss EUR and GBP symbols. The euro sign is read as `R`, and the pound sign as `W` or `B`. That turns `€14.07` into `814.07` before the subtotal correction fixes the total.

Three EUR or GBP receipts out of twelve fail on currency, which matches the 0.333 accuracy. USD receipts pass.

This is why the review screen makes currency editable. A local vision model would be the next step for symbol-level accuracy.

## Notes

- The receipts are clean and generated. Real crumpled paper, handwriting, and thermal receipts are harder.
- The subtotal correction uses subtotal plus tax when the total is implausibly far from it. It fixed three corrupted totals.
- The benchmark is small. Treat the numbers as a regression check, not a public leaderboard.

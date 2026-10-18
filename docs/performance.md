# Extraction performance

Measured on an Apple Silicon Mac with 8 GB RAM using the 12-receipt benchmark set and `benchmarks/bench_extraction.py --backends rapidocr`.

| Metric | Value |
|---|---:|
| Receipts | 12 |
| Total time | 6.04 s |
| Mean per receipt | about 0.50 s |
| Overall field accuracy | 0.806 |

Field accuracy:

| Field | Accuracy |
|---|---:|
| Date | 1.000 |
| Total | 1.000 |
| Tax | 1.000 |
| Invoice number | 1.000 |
| Merchant | 0.667 |
| Currency | 0.333 |
| Tax | 0.833 |

Merchant improved after the fixture generator switched to a font with proper word spacing. Currency is still weak because RapidOCR drops `€` and `£` while reading `$`. The benchmark now skips an OCR backend that is not installed instead of crashing, so it runs with RapidOCR alone.

Indra is optional and faster, but is not installed in this environment.

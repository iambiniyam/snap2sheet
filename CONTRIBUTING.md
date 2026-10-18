# Contributing

Thanks for taking a look. Small, focused pull requests are easiest to review.

## Development setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pytest -q
```

## Before opening a pull request

- Run the test suite.
- Add a test for any extraction change.
- Update the README if a command, flag, or output changes.

## Sample receipts

Use generated receipts or fully fake data. Do not commit real receipts with names, card numbers, or addresses.

## Bug reports

Include the command you ran, the Python version, and the receipt image if it is safe to share. If the image is private, describe the layout instead.

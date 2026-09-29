# expense-tracker

A small command-line expense tracker in pure Python. Expenses are stored in a
plain CSV file, so you can also open them in Excel or Google Sheets.

## Usage

```bash
python expenses.py add 120 food market shopping
python expenses.py add 45.5 transport taxi
python expenses.py list
python expenses.py summary            # current month
python expenses.py summary 2026-08    # a specific month
```

Example summary:

```
Summary for 2026-09
  food             180.00  ####################
  transport         45.50  #####
  total            225.50
```

Use `--file path/to/file.csv` to keep separate ledgers.

## Tests

```bash
pip install pytest
pytest
```

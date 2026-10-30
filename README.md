# expense-tracker

A small command-line expense tracker in pure Python. Expenses are stored in a
plain CSV file, so you can also open them in Excel or Google Sheets.

## Usage

```bash
python expenses.py add 120 food market shopping
python expenses.py add 45.5 transport taxi
python expenses.py list                      # rows are numbered: #1, #2, ...
python expenses.py edit 2 --amount 12.5 --note "taxi home"
python expenses.py rm 3
python expenses.py list --category food --month 2026-09
python expenses.py list --search taxi      # notes containing "taxi", any case
python expenses.py summary            # current month
python expenses.py summary 2026-08    # a specific month
python expenses.py summary --json summary.json
```

Example summary:

```
Summary for 2026-09
  food             180.00  ####################
  transport         45.50  #####
  total            225.50
```

### Report

```bash
python expenses.py report 2026-10 -o october.md
```

Writes a Markdown report for the month: the total and its change from the previous
month, a table per category with its share and budget use, and the largest expenses.
Handy for pasting into notes or a GitHub issue.

### Import

```bash
python expenses.py import phone.csv --dry-run   # show what would be added
python expenses.py import phone.csv
```

Merges another ledger in the same CSV format into the current one. A row is
skipped when the ledger already has one with the same date, amount, category
and note, so importing the same file twice adds nothing. (Two genuinely
identical expenses on the same day need different notes to both be kept.)

### Trend

```bash
python expenses.py trend              # last 6 months, all categories
python expenses.py trend food -n 12   # one category, last 12 months
```

```
Monthly totals for food
  2026-08       210.00  ##############
  2026-09       300.00  ####################
  2026-10       180.00  ############
  average       230.00
```

### Budgets

```bash
python expenses.py budget set food 300   # monthly budget per category
python expenses.py budget                # list budgets
python expenses.py budget rm food
```

`summary` then shows how much of each budget is used, and `add` warns when a
category goes over its budget for the month:

```
  food             330.00  ####################  110% of 300.00  OVER BUDGET by 30.00
```

Budgets are stored next to the ledger (`expenses.budgets.json`).

`rm` and `edit` use the numbers shown by `list` (they stay the same when you filter with
`--category` / `--month`). Both rewrite the ledger through a temporary file, so an
interrupted write can't leave it half-written.

Use `--file path/to/file.csv` to keep separate ledgers.

## Tests

```bash
pip install pytest
pytest
```

![tests](https://github.com/kayaal34/expense-tracker/actions/workflows/tests.yml/badge.svg)

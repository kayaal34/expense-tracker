# expense-tracker

A small command-line expense tracker in pure Python. Expenses are stored in a
plain CSV file, so you can also open them in Excel or Google Sheets.

## Usage

```bash
python expenses.py add 120 food market shopping
python expenses.py add 45.5 transport taxi
python expenses.py list
python expenses.py list --category food --month 2026-09
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

Use `--file path/to/file.csv` to keep separate ledgers.

## Tests

```bash
pip install pytest
pytest
```

![tests](https://github.com/kayaal34/expense-tracker/actions/workflows/tests.yml/badge.svg)

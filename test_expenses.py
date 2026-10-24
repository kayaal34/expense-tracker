from datetime import date

import pytest

import expenses


def test_append_and_read(tmp_path):
    path = tmp_path / "e.csv"
    expenses.append_expense(path, 12.5, "Food", "lunch", day=date(2026, 9, 1))
    rows = expenses.read_expenses(path)
    assert rows == [{"date": "2026-09-01", "amount": 12.5, "category": "food", "note": "lunch"}]


def test_negative_amount_rejected(tmp_path):
    with pytest.raises(ValueError):
        expenses.append_expense(tmp_path / "e.csv", -5, "food")


def test_monthly_summary_filters_by_month(tmp_path):
    path = tmp_path / "e.csv"
    expenses.append_expense(path, 10, "food", day=date(2026, 9, 1))
    expenses.append_expense(path, 5, "food", day=date(2026, 9, 20))
    expenses.append_expense(path, 7, "bills", day=date(2026, 9, 3))
    expenses.append_expense(path, 99, "food", day=date(2026, 8, 31))
    total, by_category = expenses.monthly_summary(expenses.read_expenses(path), "2026-09")
    assert total == 22
    assert by_category == {"food": 15, "bills": 7}


def test_bar_scales_to_width():
    assert expenses.bar(10, 10, width=20) == "#" * 20
    assert expenses.bar(5, 10, width=20) == "#" * 10
    assert expenses.bar(0, 0) == ""


def test_filter_expenses(tmp_path):
    path = tmp_path / "e.csv"
    expenses.append_expense(path, 10, "food", day=date(2026, 9, 1))
    expenses.append_expense(path, 7, "bills", day=date(2026, 9, 3))
    expenses.append_expense(path, 99, "food", day=date(2026, 8, 31))
    rows = expenses.read_expenses(path)
    assert [r["amount"] for r in expenses.filter_expenses(rows, "FOOD")] == [10, 99]
    assert [r["amount"] for r in expenses.filter_expenses(rows, "food", "2026-09")] == [10]


def test_export_summary(tmp_path):
    import json
    path = tmp_path / "e.csv"
    expenses.append_expense(path, 10.004, "food", day=date(2026, 9, 1))
    out = tmp_path / "summary.json"
    expenses.export_summary(expenses.read_expenses(path), "2026-09", out)
    assert json.loads(out.read_text(encoding="utf-8")) == {
        "month": "2026-09", "total": 10.0, "categories": {"food": 10.0}}


def test_budgets_roundtrip(tmp_path):
    path = expenses.budget_path(tmp_path / "e.csv")
    assert path.name == "e.budgets.json"
    assert expenses.load_budgets(path) == {}
    budgets = expenses.set_budget({}, "Food", 300)
    expenses.save_budgets(path, budgets)
    assert expenses.load_budgets(path) == {"food": 300}


def test_budget_must_be_positive():
    with pytest.raises(ValueError):
        expenses.set_budget({}, "food", 0)


def test_budget_cli(tmp_path, capsys):
    ledger = tmp_path / "e.csv"
    expenses.main(["--file", str(ledger), "budget", "set", "Food", "250"])
    expenses.main(["--file", str(ledger), "budget"])
    assert "food" in capsys.readouterr().out
    expenses.main(["--file", str(ledger), "budget", "rm", "food"])
    with pytest.raises(SystemExit):
        expenses.main(["--file", str(ledger), "budget", "rm", "food"])


def test_budget_status():
    assert expenses.budget_status(150, 300) == "50% of 300.00"
    assert expenses.budget_status(330, 300) == "110% of 300.00  OVER BUDGET by 30.00"


def test_summary_shows_budget_and_add_warns(tmp_path, capsys):
    ledger = tmp_path / "e.csv"
    month = date.today().strftime("%Y-%m")
    expenses.main(["--file", str(ledger), "budget", "set", "food", "100"])
    expenses.main(["--file", str(ledger), "add", "80", "food"])
    assert "Warning" not in capsys.readouterr().out
    expenses.main(["--file", str(ledger), "add", "40", "food"])
    assert "over its budget" in capsys.readouterr().out
    expenses.main(["--file", str(ledger), "summary", month])
    out = capsys.readouterr().out
    assert "120% of 100.00  OVER BUDGET by 20.00" in out


def test_previous_months_crosses_year():
    assert expenses.previous_months("2026-02", 4) == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_monthly_trend(tmp_path):
    path = tmp_path / "e.csv"
    expenses.append_expense(path, 10, "food", day=date(2026, 8, 3))
    expenses.append_expense(path, 20, "food", day=date(2026, 9, 3))
    expenses.append_expense(path, 5, "bills", day=date(2026, 9, 9))
    expenses.append_expense(path, 99, "food", day=date(2026, 5, 1))  # outside the window
    rows = expenses.read_expenses(path)
    months = expenses.previous_months("2026-10", 3)
    assert expenses.monthly_trend(rows, months, "Food") == {"2026-08": 10, "2026-09": 20, "2026-10": 0}
    assert expenses.monthly_trend(rows, months) == {"2026-08": 10, "2026-09": 25, "2026-10": 0}


def test_trend_cli(tmp_path, capsys):
    ledger = tmp_path / "e.csv"
    expenses.append_expense(ledger, 30, "food", day=date(2026, 9, 3))
    expenses.main(["--file", str(ledger), "trend", "food", "-n", "2", "--until", "2026-10"])
    out = capsys.readouterr().out
    assert "2026-09       30.00  ####################" in out
    assert "average       15.00" in out

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


def test_import_skips_duplicates(tmp_path):
    ledger, other = tmp_path / "a.csv", tmp_path / "b.csv"
    expenses.append_expense(ledger, 10, "food", "lunch", day=date(2026, 10, 1))
    expenses.append_expense(other, 10, "Food", "lunch", day=date(2026, 10, 1))  # same expense
    expenses.append_expense(other, 10, "food", "dinner", day=date(2026, 10, 1))
    expenses.append_expense(other, 7.5, "bills", day=date(2026, 10, 2))
    expenses.append_expense(other, 7.5, "bills", day=date(2026, 10, 2))  # duplicate within source
    assert expenses.import_expenses(ledger, other) == (2, 2)
    assert expenses.import_expenses(ledger, other) == (0, 4)
    assert [(r["category"], r["amount"], r["note"]) for r in expenses.read_expenses(ledger)] == [
        ("food", 10.0, "lunch"), ("food", 10.0, "dinner"), ("bills", 7.5, "")]


def test_import_into_new_ledger_and_self(tmp_path, capsys):
    ledger, other = tmp_path / "new.csv", tmp_path / "b.csv"
    expenses.append_expense(other, 3, "coffee", day=date(2026, 10, 3))
    expenses.main(["--file", str(ledger), "import", str(other)])
    assert "Imported 1 expense(s), skipped 0" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        expenses.main(["--file", str(ledger), "import", str(ledger)])


def test_import_dry_run_writes_nothing(tmp_path, capsys):
    ledger, other = tmp_path / "a.csv", tmp_path / "b.csv"
    expenses.append_expense(other, 3, "coffee", day=date(2026, 10, 3))
    expenses.main(["--file", str(ledger), "import", "--dry-run", str(other)])
    assert "Would import 1 expense(s)" in capsys.readouterr().out
    assert not ledger.exists()


def _ledger(tmp_path):
    path = tmp_path / "e.csv"
    expenses.append_expense(path, 10, "food", "lunch", day=date(2026, 10, 1))
    expenses.append_expense(path, 25, "bills", "phone", day=date(2026, 10, 2))
    expenses.append_expense(path, 4.5, "food", "coffee", day=date(2026, 10, 3))
    return path


def test_delete_expense(tmp_path):
    path = _ledger(tmp_path)
    removed = expenses.delete_expense(path, 2)
    assert removed["note"] == "phone"
    assert [r["note"] for r in expenses.read_expenses(path)] == ["lunch", "coffee"]
    with pytest.raises(SystemExit):
        expenses.delete_expense(path, 3)
    with pytest.raises(SystemExit):
        expenses.delete_expense(path, 0)


def test_edit_expense(tmp_path):
    path = _ledger(tmp_path)
    expenses.edit_expense(path, 3, amount=5, category="Drinks", day=date(2026, 10, 4))
    row = expenses.read_expenses(path)[2]
    assert row == {"date": "2026-10-04", "amount": 5.0, "category": "drinks", "note": "coffee"}
    with pytest.raises(ValueError):
        expenses.edit_expense(path, 1, amount=-1)
    # nothing else changed and no temporary files are left behind
    assert [r["note"] for r in expenses.read_expenses(path)] == ["lunch", "phone", "coffee"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["e.csv"]


def test_list_numbers_survive_filtering(tmp_path, capsys):
    path = _ledger(tmp_path)
    expenses.main(["--file", str(path), "list", "--category", "food"])
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("#1 ") and out[1].startswith("#3 ")
    expenses.main(["--file", str(path), "rm", "3"])
    assert "Deleted #3: 2026-10-03 4.50 food coffee" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        expenses.main(["--file", str(path), "edit", "1"])


def test_markdown_report(tmp_path):
    path = tmp_path / "e.csv"
    expenses.append_expense(path, 100, "food", day=date(2026, 9, 5))
    expenses.append_expense(path, 90, "food", "market", day=date(2026, 10, 2))
    expenses.append_expense(path, 30, "bills", "phone", day=date(2026, 10, 4))
    expenses.append_expense(path, 30, "fun", day=date(2026, 10, 9))
    report = expenses.markdown_report(expenses.read_expenses(path), "2026-10", {"food": 80}, top=2)
    lines = report.splitlines()
    assert lines[0] == "# Expenses 2026-10"
    assert lines[2] == "**Total:** 150.00 (+50% vs 2026-09)"
    assert "| food | 90.00 | 60% | 112% of 80.00  OVER BUDGET by 10.00 |" in lines
    assert "| bills | 30.00 | 20% |  |" in lines
    assert lines[-2:] == ["- 2026-10-02 **90.00** food (market)", "- 2026-10-04 **30.00** bills (phone)"]


def test_markdown_report_empty_month(tmp_path):
    report = expenses.markdown_report([], "2026-10")
    assert report.splitlines()[:3] == ["# Expenses 2026-10", "", "**Total:** 0.00"]
    assert "Largest" not in report


def test_report_cli(tmp_path, capsys):
    ledger = tmp_path / "e.csv"
    out = tmp_path / "report.md"
    expenses.append_expense(ledger, 12, "food", day=date(2026, 10, 2))
    expenses.main(["--file", str(ledger), "budget", "set", "food", "10"])
    expenses.main(["--file", str(ledger), "report", "2026-10", "-o", str(out)])
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Expenses 2026-10") and "OVER BUDGET by 2.00" in text


def test_filter_by_note_ignores_case():
    rows = [
        {"date": "2026-09-01", "amount": 5.0, "category": "food", "note": "Market run"},
        {"date": "2026-09-02", "amount": 7.0, "category": "fun", "note": "cinema"},
    ]
    assert [r["note"] for r in expenses.filter_expenses(rows, search="market")] == ["Market run"]
    assert expenses.filter_expenses(rows, search="absent") == []


def test_list_search_keeps_ledger_numbers(tmp_path, capsys):
    ledger = tmp_path / "e.csv"
    expenses.main(["--file", str(ledger), "add", "5", "food", "bread"])
    expenses.main(["--file", str(ledger), "add", "9", "transport", "Taxi", "home"])
    capsys.readouterr()
    expenses.main(["--file", str(ledger), "list", "--search", "taxi"])
    out = capsys.readouterr().out
    assert "#2" in out and "bread" not in out and "1 expense(s), total 9.00" in out


def test_largest_expenses_breaks_ties_by_newest():
    rows = [
        {"date": "2026-09-01", "amount": 5.0, "category": "a", "note": "old"},
        {"date": "2026-09-09", "amount": 5.0, "category": "a", "note": "new"},
        {"date": "2026-09-02", "amount": 9.0, "category": "b", "note": "big"},
        {"date": "2026-09-03", "amount": 1.0, "category": "c", "note": "small"},
    ]
    assert [r["note"] for r in expenses.largest_expenses(rows, 3)] == ["big", "new", "old"]

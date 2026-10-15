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

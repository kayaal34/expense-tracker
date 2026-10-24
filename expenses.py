"""Track personal expenses in a CSV file and print monthly summaries."""

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

FIELDS = ["date", "amount", "category", "note"]
DEFAULT_FILE = Path("expenses.csv")


def read_expenses(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["amount"] = float(row["amount"])
    return rows


def append_expense(path, amount, category, note="", day=None):
    if amount <= 0:
        raise ValueError("amount must be positive")
    new_file = not path.exists()
    row = {
        "date": (day or date.today()).isoformat(),
        "amount": f"{amount:.2f}",
        "category": category.lower(),
        "note": note,
    }
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    return row


def filter_expenses(rows, category=None, month=None):
    if category:
        rows = [r for r in rows if r["category"] == category.lower()]
    if month:
        rows = [r for r in rows if r["date"].startswith(month)]
    return rows


def monthly_summary(rows, month):
    """Return (total, {category: amount}) for a YYYY-MM month."""
    by_category = defaultdict(float)
    for row in rows:
        if row["date"].startswith(month):
            by_category[row["category"]] += row["amount"]
    return sum(by_category.values()), dict(by_category)


def export_summary(rows, month, out_path):
    total, by_category = monthly_summary(rows, month)
    data = {"month": month, "total": round(total, 2),
            "categories": {k: round(v, 2) for k, v in sorted(by_category.items())}}
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def previous_months(month, count):
    """The *count* months ending with *month* (YYYY-MM), oldest first."""
    year, mon = map(int, month.split("-"))
    months = []
    for _ in range(count):
        months.append(f"{year:04d}-{mon:02d}")
        year, mon = (year - 1, 12) if mon == 1 else (year, mon - 1)
    return months[::-1]


def monthly_trend(rows, months, category=None):
    """Total spent per month (optionally for one category), in the order of *months*."""
    totals = dict.fromkeys(months, 0.0)
    for row in filter_expenses(rows, category):
        month = row["date"][:7]
        if month in totals:
            totals[month] += row["amount"]
    return totals


def budget_path(expenses_path):
    """Budgets live next to the ledger: expenses.csv -> expenses.budgets.json."""
    return expenses_path.with_suffix(".budgets.json")


def load_budgets(path):
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_budgets(path, budgets):
    with path.open("w", encoding="utf-8") as f:
        json.dump(dict(sorted(budgets.items())), f, indent=2, ensure_ascii=False)


def set_budget(budgets, category, amount):
    if amount <= 0:
        raise ValueError("budget must be positive")
    budgets[category.lower()] = round(amount, 2)
    return budgets


def budget_status(spent, budget):
    """Short text comparing spending with a budget, e.g. '60% of 300.00'."""
    used = spent / budget * 100
    text = f"{used:.0f}% of {budget:.2f}"
    return f"{text}  OVER BUDGET by {spent - budget:.2f}" if spent > budget else text


def bar(value, maximum, width=20):
    filled = round(width * value / maximum) if maximum else 0
    return "#" * filled


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simple expense tracker")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="record an expense")
    p_add.add_argument("amount", type=float)
    p_add.add_argument("category")
    p_add.add_argument("note", nargs="*")

    p_list = sub.add_parser("list", help="show expenses")
    p_list.add_argument("-c", "--category", help="only show this category")
    p_list.add_argument("-m", "--month", help="only show this month (YYYY-MM)")

    p_sum = sub.add_parser("summary", help="totals per category for a month")
    p_sum.add_argument("month", nargs="?", default=date.today().strftime("%Y-%m"),
                       help="month as YYYY-MM (default: current month)")
    p_sum.add_argument("--json", type=Path, metavar="FILE", help="also write the summary to a JSON file")

    p_trend = sub.add_parser("trend", help="monthly totals over the last months")
    p_trend.add_argument("category", nargs="?", help="only this category (default: everything)")
    p_trend.add_argument("-n", "--months", type=int, default=6, help="how many months (default: 6)")
    p_trend.add_argument("--until", default=date.today().strftime("%Y-%m"),
                         help="last month to show, YYYY-MM (default: current month)")

    p_budget = sub.add_parser("budget", help="show or change monthly budgets per category")
    budget_sub = p_budget.add_subparsers(dest="budget_command")
    p_bset = budget_sub.add_parser("set", help="set the monthly budget for a category")
    p_bset.add_argument("category")
    p_bset.add_argument("amount", type=float)
    p_brm = budget_sub.add_parser("rm", help="remove the budget for a category")
    p_brm.add_argument("category")

    args = parser.parse_args(argv)

    if args.command == "add":
        row = append_expense(args.file, args.amount, args.category, " ".join(args.note))
        print(f"Saved {row['amount']} in '{row['category']}'")
        budget = load_budgets(budget_path(args.file)).get(row["category"])
        if budget:
            month = row["date"][:7]
            _, by_category = monthly_summary(read_expenses(args.file), month)
            spent = by_category.get(row["category"], 0)
            if spent > budget:
                print(f"Warning: '{row['category']}' is over its budget for {month}: {budget_status(spent, budget)}")
    elif args.command == "list":
        rows = filter_expenses(read_expenses(args.file), args.category, args.month)
        for row in rows:
            print(f"{row['date']}  {row['amount']:>10.2f}  {row['category']:<12} {row['note']}")
        print(f"{len(rows)} expense(s), total {sum(r['amount'] for r in rows):.2f}")
    elif args.command == "summary":
        total, by_category = monthly_summary(read_expenses(args.file), args.month)
        if not by_category:
            print(f"No expenses for {args.month}.")
            return
        top = max(by_category.values())
        budgets = load_budgets(budget_path(args.file))
        print(f"Summary for {args.month}")
        for category, amount in sorted(by_category.items(), key=lambda kv: -kv[1]):
            line = f"  {category:<12} {amount:>10.2f}  {bar(amount, top):<20}"
            if category in budgets:
                line += f"  {budget_status(amount, budgets[category])}"
            print(line.rstrip())
        print(f"  {'total':<12} {total:>10.2f}")
        if args.json:
            export_summary(read_expenses(args.file), args.month, args.json)
            print(f"Saved summary to {args.json}")

    elif args.command == "trend":
        if args.months < 1:
            raise SystemExit("--months must be at least 1")
        totals = monthly_trend(read_expenses(args.file), previous_months(args.until, args.months), args.category)
        top = max(totals.values())
        label = args.category.lower() if args.category else "all categories"
        print(f"Monthly totals for {label}")
        for month, amount in totals.items():
            print(f"  {month}  {amount:>10.2f}  {bar(amount, top)}".rstrip())
        print(f"  {'average':<7}  {sum(totals.values()) / len(totals):>10.2f}")
    elif args.command == "budget":
        path = budget_path(args.file)
        budgets = load_budgets(path)
        if args.budget_command == "set":
            set_budget(budgets, args.category, args.amount)
            save_budgets(path, budgets)
            print(f"Budget for '{args.category.lower()}' set to {budgets[args.category.lower()]:.2f} per month")
        elif args.budget_command == "rm":
            if budgets.pop(args.category.lower(), None) is None:
                raise SystemExit(f"No budget for '{args.category.lower()}'")
            save_budgets(path, budgets)
            print(f"Removed budget for '{args.category.lower()}'")
        elif not budgets:
            print("No budgets set. Use: budget set <category> <amount>")
        else:
            for category, amount in budgets.items():
                print(f"  {category:<12} {amount:>10.2f}")


if __name__ == "__main__":
    main()

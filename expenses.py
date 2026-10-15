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

    args = parser.parse_args(argv)

    if args.command == "add":
        row = append_expense(args.file, args.amount, args.category, " ".join(args.note))
        print(f"Saved {row['amount']} in '{row['category']}'")
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
        print(f"Summary for {args.month}")
        for category, amount in sorted(by_category.items(), key=lambda kv: -kv[1]):
            print(f"  {category:<12} {amount:>10.2f}  {bar(amount, top)}")
        print(f"  {'total':<12} {total:>10.2f}")
        if args.json:
            export_summary(read_expenses(args.file), args.month, args.json)
            print(f"Saved summary to {args.json}")


if __name__ == "__main__":
    main()

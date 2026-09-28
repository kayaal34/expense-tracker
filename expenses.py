"""Track personal expenses in a CSV file and print monthly summaries."""

import argparse
import csv
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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simple expense tracker")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="record an expense")
    p_add.add_argument("amount", type=float)
    p_add.add_argument("category")
    p_add.add_argument("note", nargs="*")

    sub.add_parser("list", help="show all expenses")

    args = parser.parse_args(argv)

    if args.command == "add":
        row = append_expense(args.file, args.amount, args.category, " ".join(args.note))
        print(f"Saved {row['amount']} in '{row['category']}'")
    elif args.command == "list":
        for row in read_expenses(args.file):
            print(f"{row['date']}  {row['amount']:>10.2f}  {row['category']:<12} {row['note']}")


if __name__ == "__main__":
    main()

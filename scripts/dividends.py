# /// script
# dependencies = ["avanza-api"]
# ///
"""
Dividend tracker: all dividend payments grouped by stock for a given year.

Usage: uv run dividends.py [YYYY]
Default: current year.
"""

import os
import sys
from collections import defaultdict
from datetime import date


def check_credentials():
    missing = [v for v in ("AVANZA_USERNAME", "AVANZA_PASSWORD", "AVANZA_TOTP_SECRET") if not os.getenv(v)]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Run: export AVANZA_USERNAME=... AVANZA_PASSWORD=... AVANZA_TOTP_SECRET=...", file=sys.stderr)
        sys.exit(1)


def fmt(value, decimals=2):
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}"


def main():
    check_credentials()

    year_arg = sys.argv[1] if len(sys.argv) > 1 else str(date.today().year)
    try:
        year = int(year_arg)
    except ValueError:
        print(f"ERROR: Invalid year '{year_arg}'. Use YYYY format.", file=sys.stderr)
        sys.exit(1)

    date_from = date(year, 1, 1)
    date_to = date(year, 12, 31)

    from avanza import Avanza, TransactionsDetailsType

    avanza = Avanza({
        "username": os.environ["AVANZA_USERNAME"],
        "password": os.environ["AVANZA_PASSWORD"],
        "totpSecret": os.environ["AVANZA_TOTP_SECRET"],
    })

    result = avanza.get_transactions_details(
        transaction_details_types=[TransactionsDetailsType.DIVIDEND],
        transactions_from=date_from,
        transactions_to=date_to,
        max_elements=1000,
    )
    transactions = result.transactions if hasattr(result, "transactions") else result

    if not transactions:
        print(f"No dividend payments found in {year}.")
        return

    # Group by instrument name (use isin as fallback key)
    # Key: (isin or name) → {name, payments: [(date, amount)]}
    by_stock: dict[str, dict] = defaultdict(lambda: {"name": "", "payments": []})

    for txn in transactions:
        key = txn.isin or txn.instrumentName or txn.description or "unknown"
        entry = by_stock[key]
        if not entry["name"]:
            entry["name"] = txn.instrumentName or txn.description or key
        pay_date = txn.tradeDate or txn.settlementDate or (txn.date[:10] if txn.date else "—")
        amount = txn.amount.value if txn.amount and txn.amount.value else 0.0
        entry["payments"].append((pay_date, amount))

    print(f"## Dividend Income — {year}\n")

    col_w = [28, 8, 14, 14]
    header = (
        f"{'Stock':<{col_w[0]}} {'Payments':>{col_w[1]}} "
        f"{'Total (SEK)':>{col_w[2]}} {'Latest date':>{col_w[3]}}"
    )
    sep = "  ".join("-" * w for w in col_w)
    print(header)
    print(sep)

    grand_total = 0.0
    rows = []
    for isin, entry in by_stock.items():
        total = sum(amt for _, amt in entry["payments"])
        grand_total += total
        latest = max(d for d, _ in entry["payments"])
        rows.append((entry["name"], len(entry["payments"]), total, latest))

    # Sort by total descending
    rows.sort(key=lambda r: r[2], reverse=True)

    for name, count, total, latest in rows:
        name_str = name[:col_w[0]]
        print(
            f"{name_str:<{col_w[0]}}  {count:>{col_w[1]}}  "
            f"{fmt(total):>{col_w[2]}}  {latest:>{col_w[3]}}"
        )

    print(sep)
    total_payments = sum(r[1] for r in rows)
    print(
        f"{'TOTAL':<{col_w[0]}}  {total_payments:>{col_w[1]}}  "
        f"{fmt(grand_total):>{col_w[2]}}"
    )

    # Monthly breakdown
    monthly: dict[str, float] = defaultdict(float)
    for entry in by_stock.values():
        for pay_date, amt in entry["payments"]:
            month_key = str(pay_date)[:7] if pay_date != "—" else "unknown"
            monthly[month_key] += amt

    if monthly:
        print("\n### By Month\n")
        for month in sorted(monthly):
            print(f"  {month}: {fmt(monthly[month])} SEK")


if __name__ == "__main__":
    main()

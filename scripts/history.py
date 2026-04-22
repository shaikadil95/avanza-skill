# /// script
# dependencies = ["avanza-api"]
# ///
"""
Trade history viewer: read-only analysis of past BUY/SELL/DIVIDEND/DEPOSIT events.

Usage: uv run history.py [from-date] [to-date]
Default: current month.
"""

import os
import sys
from datetime import date, timedelta


def check_credentials():
    missing = [v for v in ("AVANZA_USERNAME", "AVANZA_PASSWORD", "AVANZA_TOTP_SECRET") if not os.getenv(v)]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Run: export AVANZA_USERNAME=... AVANZA_PASSWORD=... AVANZA_TOTP_SECRET=...", file=sys.stderr)
        sys.exit(1)


def parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        print(f"ERROR: Invalid date '{s}'. Use YYYY-MM-DD format.", file=sys.stderr)
        sys.exit(1)


def fmt(value, decimals=2):
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}"


def gv(d, *keys, default=None):
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
        if d is default:
            return default
    return d


def main():
    check_credentials()

    today = date.today()
    date_from = date(today.year, today.month, 1)
    date_to = today

    args = sys.argv[1:]
    if len(args) >= 1:
        date_from = parse_date(args[0])
    if len(args) >= 2:
        date_to = parse_date(args[1])

    if date_from > date_to:
        print(f"ERROR: from-date {date_from} is after to-date {date_to}.", file=sys.stderr)
        sys.exit(1)

    from avanza import Avanza

    avanza = Avanza({
        "username": os.environ["AVANZA_USERNAME"],
        "password": os.environ["AVANZA_PASSWORD"],
        "totpSecret": os.environ["AVANZA_TOTP_SECRET"],
    }, retry_with_next_otp=True)

    result = avanza.get_transactions_details(
        transactions_from=date_from,
        transactions_to=date_to,
        max_elements=1000,
    )

    if isinstance(result, dict):
        transactions = result.get("transactions", [])
    elif hasattr(result, "transactions"):
        transactions = result.transactions
    else:
        transactions = result or []

    print(f"## Transactions  {date_from} → {date_to}\n")

    if not transactions:
        print("No transactions found in this period.")
        return

    # Sort by trade date descending
    def sort_key(t):
        if isinstance(t, dict):
            return t.get("tradeDate") or t.get("date") or ""
        return t.tradeDate or t.date or ""

    transactions = sorted(transactions, key=sort_key, reverse=True)

    col_w = [10, 24, 12, 8, 10, 12, 10]
    header = (
        f"{'Date':<{col_w[0]}} {'Instrument':<{col_w[1]}} "
        f"{'Type':<{col_w[2]}} {'Shares':>{col_w[3]}} "
        f"{'Price':>{col_w[4]}} {'Amount':>{col_w[5]}} {'Commission':>{col_w[6]}}"
    )
    sep = "  ".join("-" * w for w in col_w)
    print(header)
    print(sep)

    total_amount = 0.0
    total_commission = 0.0

    for txn in transactions:
        if isinstance(txn, dict):
            raw_date = txn.get("tradeDate") or txn.get("date") or "—"
            trade_date = str(raw_date)[:10]
            name = (txn.get("instrumentName") or txn.get("description") or "—")[:col_w[1]]
            txn_type = (txn.get("type") or "—")[:col_w[2]]
            volume = gv(txn, "volume", "value")
            price = gv(txn, "priceInTransactionCurrency", "value")
            amount = gv(txn, "amount", "value")
            commission = gv(txn, "commission", "value")
        else:
            trade_date = txn.tradeDate or (txn.date[:10] if txn.date else "—")
            name = (txn.instrumentName or txn.description or "—")[:col_w[1]]
            txn_type = (txn.type or "—")[:col_w[2]]
            volume = txn.volume.value if txn.volume else None
            price = txn.priceInTransactionCurrency.value if txn.priceInTransactionCurrency else None
            amount = txn.amount.value if txn.amount else None
            commission = txn.commission.value if txn.commission else None

        if amount:
            total_amount += amount
        if commission:
            total_commission += commission

        vol_str = fmt(volume, 0) if volume and volume == int(volume) else fmt(volume) if volume else "—"

        print(
            f"{trade_date:<{col_w[0]}}  {name:<{col_w[1]}}  "
            f"{txn_type:<{col_w[2]}}  {vol_str:>{col_w[3]}}  "
            f"{fmt(price):>{col_w[4]}}  {fmt(amount):>{col_w[5]}}  {fmt(commission):>{col_w[6]}}"
        )

    print(sep)
    print(f"{'TOTAL':<{col_w[0]}}  {'':>{col_w[1]+col_w[2]+col_w[3]+col_w[4]+6}}  {fmt(total_amount):>{col_w[5]}}  {fmt(total_commission):>{col_w[6]}}")
    print(f"\n{len(transactions)} transaction(s) in period.")


if __name__ == "__main__":
    main()

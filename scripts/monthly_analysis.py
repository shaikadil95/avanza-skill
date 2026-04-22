# /// script
# dependencies = ["avanza-api"]
# ///
"""
Monthly investment analysis: show what was deployed as cash in a given month
and what those specific shares are worth today.

Usage: uv run monthly_analysis.py [YYYY-MM]
Default month: previous calendar month.
"""

import os
import sys
from collections import defaultdict
from datetime import date, timedelta


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


def gv(d, *keys, default=None):
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
        if d is default:
            return default
    return d


def month_bounds(ym: str) -> tuple[date, date]:
    """Return (first_day, last_day) for a YYYY-MM string."""
    try:
        year, month = int(ym[:4]), int(ym[5:7])
    except (ValueError, IndexError):
        print(f"ERROR: Invalid month '{ym}'. Use YYYY-MM format.", file=sys.stderr)
        sys.exit(1)
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last


def prev_month_str() -> str:
    today = date.today()
    first_this = date(today.year, today.month, 1)
    last_prev = first_this - timedelta(days=1)
    return f"{last_prev.year}-{last_prev.month:02d}"


def main():
    check_credentials()

    month_arg = sys.argv[1] if len(sys.argv) > 1 else prev_month_str()
    date_from, date_to = month_bounds(month_arg)

    from avanza import Avanza
    from avanza.constants import TransactionsDetailsType

    avanza = Avanza({
        "username": os.environ["AVANZA_USERNAME"],
        "password": os.environ["AVANZA_PASSWORD"],
        "totpSecret": os.environ["AVANZA_TOTP_SECRET"],
    }, retry_with_next_otp=True)

    # --- 1. Fetch BUY transactions for the month ---
    result = avanza.get_transactions_details(
        transaction_details_types=[TransactionsDetailsType.BUY],
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

    if not transactions:
        print(f"No BUY transactions found in {month_arg}.")
        return

    # --- 2. Group by ISIN: sum shares bought and total cost ---
    by_isin: dict[str, dict] = defaultdict(lambda: {"name": "", "shares": 0.0, "cost": 0.0, "ob_id": None})
    for txn in transactions:
        if isinstance(txn, dict):
            isin = txn.get("isin") or ""
            if not isin:
                continue
            entry = by_isin[isin]
            entry["name"] = txn.get("instrumentName") or entry["name"] or isin
            vol = gv(txn, "volume", "value")
            amt = gv(txn, "amount", "value")
            if vol:
                entry["shares"] += abs(vol)
            if amt:
                entry["cost"] += abs(amt)
            if not entry["ob_id"]:
                entry["ob_id"] = gv(txn, "orderbook", "id")
        else:
            isin = txn.isin or ""
            if not isin:
                continue
            entry = by_isin[isin]
            entry["name"] = txn.instrumentName or entry["name"] or isin
            if txn.volume and txn.volume.value:
                entry["shares"] += abs(txn.volume.value)
            if txn.amount and txn.amount.value:
                entry["cost"] += abs(txn.amount.value)
            if txn.orderbook and not entry["ob_id"]:
                entry["ob_id"] = txn.orderbook.id if hasattr(txn.orderbook, "id") else None

    # --- 3. Get current positions to find price per share ---
    positions_data = avanza.get_accounts_positions()
    price_by_isin: dict[str, float] = {}

    if isinstance(positions_data, dict):
        with_ob = positions_data.get("withOrderbook", [])
    else:
        with_ob = getattr(positions_data, "withOrderbook", [])

    for pos in with_ob:
        if isinstance(pos, dict):
            isin = gv(pos, "instrument", "isin")
            vol = gv(pos, "volume", "value")
            val = gv(pos, "value", "value")
        else:
            isin = pos.instrument.isin if hasattr(pos.instrument, "isin") else None
            vol = pos.volume.value if pos.volume else None
            val = pos.value.value if pos.value else None
        if isin and vol and val:
            price_by_isin[isin] = val / vol

    # For ISINs not in current positions, try market data via orderbookId
    for isin, entry in by_isin.items():
        if isin not in price_by_isin and entry["ob_id"]:
            try:
                mkt = avanza.get_market_data(entry["ob_id"])
                if isinstance(mkt, dict):
                    last = gv(mkt, "quote", "latest", "value") or gv(mkt, "quote", "last")
                else:
                    last = (mkt.quote.last if mkt and mkt.quote else None)
                if last:
                    price_by_isin[isin] = last
            except Exception:
                pass

    # --- 4. Print table ---
    print(f"## Monthly Investment Analysis — {month_arg}\n")
    print(f"Period: {date_from} → {date_to}\n")

    col_w = [24, 8, 14, 14, 12, 10, 8]
    header = (
        f"{'Stock':<{col_w[0]}} {'Shares':>{col_w[1]}} "
        f"{'Deployed':>{col_w[2]}} {'Now Worth':>{col_w[3]}} "
        f"{'Gain (SEK)':>{col_w[4]}} {'Gain %':>{col_w[5]}} {'Price?':>{col_w[6]}}"
    )
    sep = "  ".join("-" * w for w in col_w)
    print(header)
    print(sep)

    total_deployed = 0.0
    total_now = 0.0
    total_gain = 0.0
    priced_count = 0

    for isin, entry in sorted(by_isin.items(), key=lambda x: x[1]["name"]):
        name = entry["name"][:col_w[0]]
        shares = entry["shares"]
        cost = entry["cost"]
        total_deployed += cost

        current_price = price_by_isin.get(isin)
        if current_price is not None:
            now_worth = shares * current_price
            gain_sek = now_worth - cost
            gain_pct = (gain_sek / cost * 100) if cost else 0.0
            total_now += now_worth
            total_gain += gain_sek
            priced_count += 1
            price_flag = "live"
            gain_str = fmt(gain_sek)
            gain_pct_str = f"{fmt(gain_pct, 1)}%"
            now_str = fmt(now_worth)
        else:
            price_flag = "n/a"
            gain_str = "—"
            gain_pct_str = "—"
            now_str = "—"

        shares_str = fmt(shares, 0) if shares == int(shares) else fmt(shares)
        print(
            f"{name:<{col_w[0]}}  {shares_str:>{col_w[1]}}  "
            f"{fmt(cost):>{col_w[2]}}  {now_str:>{col_w[3]}}  "
            f"{gain_str:>{col_w[4]}}  {gain_pct_str:>{col_w[5]}}  {price_flag:>{col_w[6]}}"
        )

    print(sep)
    total_gain_pct = (total_gain / total_deployed * 100) if total_deployed else 0
    print(
        f"{'TOTAL':<{col_w[0]}}  {'':>{col_w[1]}}  "
        f"{fmt(total_deployed):>{col_w[2]}}  {fmt(total_now) if priced_count else '—':>{col_w[3]}}  "
        f"{fmt(total_gain) if priced_count else '—':>{col_w[4]}}  "
        f"{(fmt(total_gain_pct, 1) + '%') if priced_count else '—':>{col_w[5]}}"
    )

    unpriced = len(by_isin) - priced_count
    if unpriced:
        print(f"\nNote: {unpriced} position(s) have no current price (fully sold or delisted).")


if __name__ == "__main__":
    main()

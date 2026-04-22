# /// script
# dependencies = ["avanza-api"]
# ///
"""
Cost basis drill-down for a specific stock.

Usage: uv run costbasis.py <name_or_isin>
  <name_or_isin>  Partial stock name (case-insensitive) or exact ISIN
"""

import os
import sys


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


def main():
    check_credentials()

    if len(sys.argv) < 2:
        print("Usage: costbasis.py <name_or_isin>", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1].upper()

    from avanza import Avanza
    from avanza.constants import TransactionsDetailsType

    avanza = Avanza({
        "username": os.environ["AVANZA_USERNAME"],
        "password": os.environ["AVANZA_PASSWORD"],
        "totpSecret": os.environ["AVANZA_TOTP_SECRET"],
    }, retry_with_next_otp=True)

    # 1. Find the ISIN by matching against current positions
    positions_data = avanza.get_accounts_positions()
    if isinstance(positions_data, dict):
        with_ob = positions_data.get("withOrderbook", [])
    else:
        with_ob = getattr(positions_data, "withOrderbook", [])

    matched_isin = None
    matched_name = None
    current_price = None
    current_shares = None

    for pos in with_ob:
        if isinstance(pos, dict):
            isin = gv(pos, "instrument", "isin") or ""
            name = gv(pos, "instrument", "name") or ""
            vol = gv(pos, "volume", "value")
            val = gv(pos, "value", "value")
        else:
            isin = pos.instrument.isin if hasattr(pos.instrument, "isin") else ""
            name = pos.instrument.name if hasattr(pos.instrument, "name") else ""
            vol = pos.volume.value if pos.volume else None
            val = pos.value.value if pos.value else None

        if query == isin.upper() or query in name.upper():
            matched_isin = isin
            matched_name = name
            if vol and val:
                current_price = val / vol
                current_shares = vol
            break

    if not matched_isin:
        print(f"ERROR: No current position found matching '{sys.argv[1]}'.", file=sys.stderr)
        sys.exit(1)

    # 2. Fetch all BUY transactions for this ISIN
    result = avanza.get_transactions_details(
        transaction_details_types=[TransactionsDetailsType.BUY],
        isin=matched_isin,
        max_elements=1000,
    )

    if isinstance(result, dict):
        transactions = result.get("transactions", [])
    elif hasattr(result, "transactions"):
        transactions = result.transactions
    else:
        transactions = result or []

    if not transactions:
        print(f"No BUY transactions found for {matched_name}.")
        return

    # Sort ascending to build cumulative avg chronologically
    def txn_date(txn):
        if isinstance(txn, dict):
            return txn.get("tradeDate") or txn.get("date") or ""
        return getattr(txn, "tradeDate", None) or getattr(txn, "date", None) or ""

    transactions = sorted(transactions, key=txn_date)

    # 3. Print lot table
    print(f"## Cost Basis — {matched_name}\n")
    print(f"ISIN: {matched_isin}\n")

    col_w = [10, 8, 12, 12, 12, 12, 14]
    header = (
        f"{'Date':<{col_w[0]}} {'Shares':>{col_w[1]}} "
        f"{'Price':>{col_w[2]}} {'Commission':>{col_w[3]}} "
        f"{'Lot Cost':>{col_w[4]}} {'Total Shares':>{col_w[5]}} {'Avg Price':>{col_w[6]}}"
    )
    sep = "  ".join("-" * w for w in col_w)
    print(header)
    print(sep)

    cum_shares = 0.0
    cum_cost = 0.0
    first_date = None
    first_price = None

    for txn in transactions:
        if isinstance(txn, dict):
            trade_date = txn.get("tradeDate") or txn.get("date") or "—"
            vol = gv(txn, "volume", "value")
            price = gv(txn, "priceInTransactionCurrency", "value") or gv(txn, "priceInTradedCurrency", "value")
            commission = gv(txn, "commission", "value") or 0.0
            amount = gv(txn, "amount", "value")
        else:
            trade_date = getattr(txn, "tradeDate", None) or getattr(txn, "date", None) or "—"
            vol = txn.volume.value if txn.volume else None
            price = (txn.priceInTransactionCurrency.value if txn.priceInTransactionCurrency else None) or \
                    (txn.priceInTradedCurrency.value if txn.priceInTradedCurrency else None)
            commission = (txn.commission.value if txn.commission else None) or 0.0
            amount = txn.amount.value if txn.amount else None

        if not vol:
            continue

        vol = abs(vol)
        lot_cost = abs(amount) if amount else (vol * (price or 0) + abs(commission))
        cum_shares += vol
        cum_cost += lot_cost
        avg_price = cum_cost / cum_shares if cum_shares else 0.0

        if first_date is None:
            first_date = str(trade_date)[:10]
            first_price = price

        shares_str = fmt(vol, 0) if vol == int(vol) else fmt(vol)
        print(
            f"{str(trade_date)[:col_w[0]]:<{col_w[0]}}  {shares_str:>{col_w[1]}}  "
            f"{fmt(price):>{col_w[2]}}  {fmt(abs(commission)):>{col_w[3]}}  "
            f"{fmt(lot_cost):>{col_w[4]}}  {fmt(cum_shares, 0):>{col_w[5]}}  {fmt(avg_price):>{col_w[6]}}"
        )

    print(sep)

    # 4. Summary
    avg_price_final = cum_cost / cum_shares if cum_shares else None
    print(f"\nFirst purchase : {first_date or '—'}  @  {fmt(first_price)} SEK/share")
    print(f"Total bought   : {fmt(cum_shares, 0)} shares  —  {fmt(cum_cost)} SEK")
    print(f"Avg cost basis : {fmt(avg_price_final)} SEK/share")

    if current_price is not None and avg_price_final:
        gain_per_share = current_price - avg_price_final
        gain_pct = gain_per_share / avg_price_final * 100
        unrealised = gain_per_share * (current_shares or 0)
        print(f"Current price  : {fmt(current_price)} SEK/share")
        print(f"Unrealised gain: {fmt(unrealised)} SEK  ({fmt(gain_pct, 1)}% vs avg cost)")
        if first_price:
            since_first = (current_price - first_price) / first_price * 100
            print(f"Return since 1st purchase: {fmt(since_first, 1)}%  "
                  f"(price {fmt(first_price)} → {fmt(current_price)})")


if __name__ == "__main__":
    main()

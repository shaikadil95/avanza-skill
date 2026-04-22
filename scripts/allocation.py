# /// script
# dependencies = ["avanza-api"]
# ///
"""
Portfolio allocation: asset type breakdown, sector breakdown (stocks), concentration risk,
and currency exposure.

Usage: uv run allocation.py
"""

import os
import sys
from collections import defaultdict


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


CONCENTRATION_THRESHOLD = 10.0


def main():
    check_credentials()

    from avanza import Avanza

    avanza = Avanza({
        "username": os.environ["AVANZA_USERNAME"],
        "password": os.environ["AVANZA_PASSWORD"],
        "totpSecret": os.environ["AVANZA_TOTP_SECRET"],
    }, retry_with_next_otp=True)

    # 1. Fetch all positions
    positions_data = avanza.get_accounts_positions()
    if isinstance(positions_data, dict):
        with_ob = positions_data.get("withOrderbook", [])
        cash_positions = positions_data.get("cashPositions", [])
    else:
        with_ob = getattr(positions_data, "withOrderbook", [])
        cash_positions = getattr(positions_data, "cashPositions", [])

    holdings = []
    for pos in with_ob:
        if isinstance(pos, dict):
            name = gv(pos, "instrument", "name") or "Unknown"
            isin = gv(pos, "instrument", "isin") or ""
            instr_type = gv(pos, "instrument", "type") or "UNKNOWN"
            currency = gv(pos, "instrument", "currency") or "SEK"
            ob_id = gv(pos, "instrument", "orderbook", "id")
            value = gv(pos, "value", "value") or 0.0
        else:
            name = pos.instrument.name if hasattr(pos.instrument, "name") else "Unknown"
            isin = pos.instrument.isin if hasattr(pos.instrument, "isin") else ""
            instr_type = pos.instrument.type if hasattr(pos.instrument, "type") else "UNKNOWN"
            currency = pos.instrument.currency if hasattr(pos.instrument, "currency") else "SEK"
            ob_id = (pos.instrument.orderbook.id
                     if hasattr(pos.instrument, "orderbook") and pos.instrument.orderbook else None)
            value = pos.value.value if pos.value else 0.0
        holdings.append({
            "name": name, "isin": isin, "type": instr_type,
            "currency": currency, "ob_id": ob_id, "value": value,
            "sector": None,
        })

    total_cash = 0.0
    for cash in cash_positions:
        if isinstance(cash, dict):
            total_cash += gv(cash, "totalBalance", "value") or 0.0
        else:
            total_cash += (cash.totalBalance.value if cash.totalBalance else 0.0)

    total_invested = sum(h["value"] for h in holdings)
    total_portfolio = total_invested + total_cash

    if total_portfolio == 0:
        print("No positions found.")
        return

    # 2. Fetch sector info for STOCK-type positions (one API call per stock)
    for h in holdings:
        if h["type"] == "STOCK" and h["ob_id"]:
            try:
                info = avanza.get_stock_info(h["ob_id"])
                if isinstance(info, dict):
                    sectors = info.get("sectors") or []
                    if sectors:
                        names = [s.get("sectorName") for s in sectors
                                 if isinstance(s, dict) and s.get("sectorName")]
                        h["sector"] = names[0] if names else None
                else:
                    sectors = getattr(info, "sectors", None) or []
                    if sectors:
                        first = sectors[0]
                        h["sector"] = getattr(first, "sectorName", None)
            except Exception:
                pass

    print("## Portfolio Allocation\n")

    col_w = [24, 14, 14]
    sep = "  ".join("-" * w for w in col_w)

    # --- Asset Type Breakdown ---
    by_type: dict[str, float] = defaultdict(float)
    for h in holdings:
        by_type[h["type"]] += h["value"]
    if total_cash:
        by_type["CASH"] += total_cash

    print("### Asset Type Breakdown\n")
    print(f"{'Asset Type':<{col_w[0]}} {'Value (SEK)':>{col_w[1]}} {'% Portfolio':>{col_w[2]}}")
    print(sep)
    for asset_type, val in sorted(by_type.items(), key=lambda x: -x[1]):
        pct = val / total_portfolio * 100
        print(f"{asset_type:<{col_w[0]}}  {fmt(val):>{col_w[1]}}  {fmt(pct, 1) + '%':>{col_w[2]}}")
    print(sep)
    print(f"{'TOTAL':<{col_w[0]}}  {fmt(total_portfolio):>{col_w[1]}}")

    # --- Sector Breakdown (stocks only) ---
    stock_total = sum(h["value"] for h in holdings if h["type"] == "STOCK")
    if stock_total > 0:
        by_sector: dict[str, float] = defaultdict(float)
        for h in holdings:
            if h["type"] == "STOCK":
                by_sector[h["sector"] or "Unknown"] += h["value"]

        col_w2 = [24, 14, 18]
        sep2 = "  ".join("-" * w for w in col_w2)
        print("\n### Sector Breakdown (Stocks)\n")
        print(f"{'Sector':<{col_w2[0]}} {'Value (SEK)':>{col_w2[1]}} {'% Stock Holdings':>{col_w2[2]}}")
        print(sep2)
        for sector, val in sorted(by_sector.items(), key=lambda x: -x[1]):
            pct = val / stock_total * 100
            print(f"{sector:<{col_w2[0]}}  {fmt(val):>{col_w2[1]}}  {fmt(pct, 1) + '%':>{col_w2[2]}}")

    # --- Concentration Risk ---
    risky = [
        (h["name"], h["value"], h["value"] / total_portfolio * 100, h["currency"])
        for h in holdings
        if h["value"] / total_portfolio * 100 >= CONCENTRATION_THRESHOLD
    ]

    print(f"\n### Concentration Risk  (>= {CONCENTRATION_THRESHOLD:.0f}% of portfolio)\n")
    if not risky:
        print(f"  No position exceeds {CONCENTRATION_THRESHOLD:.0f}% — well diversified.")
    else:
        col_w3 = [28, 14, 14, 10]
        sep3 = "  ".join("-" * w for w in col_w3)
        print(f"{'Position':<{col_w3[0]}} {'Value (SEK)':>{col_w3[1]}} {'% Portfolio':>{col_w3[2]}} {'Currency':>{col_w3[3]}}")
        print(sep3)
        for name, val, pct, ccy in sorted(risky, key=lambda x: -x[2]):
            flag = "  [HIGH]" if pct >= 20 else ""
            ccy_note = f"  [{ccy}]" if ccy and ccy != "SEK" else ""
            print(
                f"{name[:col_w3[0]]:<{col_w3[0]}}  {fmt(val):>{col_w3[1]}}  "
                f"{fmt(pct, 1) + '%':>{col_w3[2]}}  {ccy:>{col_w3[3]}}{flag}{ccy_note}"
            )

    # --- Currency Exposure ---
    by_currency: dict[str, float] = defaultdict(float)
    for h in holdings:
        by_currency[h["currency"]] += h["value"]
    if total_cash:
        by_currency["SEK"] += total_cash

    non_sek = {ccy: val for ccy, val in by_currency.items() if ccy != "SEK"}
    if non_sek:
        print("\n### Currency Exposure\n")
        all_ccys = sorted(by_currency.items(), key=lambda x: -x[1])
        for ccy, val in all_ccys:
            pct = val / total_portfolio * 100
            marker = "  *" if ccy != "SEK" else ""
            print(f"  {ccy}: {fmt(val)} SEK  ({fmt(pct, 1)}%){marker}")
        print("  (* non-SEK currency risk)")


if __name__ == "__main__":
    main()

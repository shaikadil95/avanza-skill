# /// script
# dependencies = ["avanza-api"]
# ///

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
    """Safely get nested dict value."""
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
        if d is default:
            return default
    return d


def main():
    check_credentials()

    from avanza import Avanza

    avanza = Avanza({
        "username": os.environ["AVANZA_USERNAME"],
        "password": os.environ["AVANZA_PASSWORD"],
        "totpSecret": os.environ["AVANZA_TOTP_SECRET"],
    }, retry_with_next_otp=True)

    positions_data = avanza.get_accounts_positions()

    # Support both dict and object-style responses
    if isinstance(positions_data, dict):
        with_ob = positions_data.get("withOrderbook", [])
        cash_positions = positions_data.get("cashPositions", [])
    else:
        with_ob = getattr(positions_data, "withOrderbook", [])
        cash_positions = getattr(positions_data, "cashPositions", [])

    print("## Holdings & Gains\n")

    col_w = [24, 6, 14, 14, 12, 10, 10]
    header = (
        f"{'Stock':<{col_w[0]}} {'Shares':>{col_w[1]}} "
        f"{'Invested':>{col_w[2]}} {'Value':>{col_w[3]}} "
        f"{'Gain (SEK)':>{col_w[4]}} {'Gain %':>{col_w[5]}} {'Day %':>{col_w[6]}}"
    )
    sep = "  ".join("-" * w for w in col_w)
    print(header)
    print(sep)

    total_invested = 0.0
    total_value = 0.0
    total_gain = 0.0

    for pos in with_ob:
        if isinstance(pos, dict):
            name = gv(pos, "instrument", "name", default="—")[:col_w[0]]
            shares = gv(pos, "volume", "value")
            invested = gv(pos, "acquiredValue", "value")
            value = gv(pos, "value", "value")
            day_pct = gv(pos, "lastTradingDayPerformance", "relative", "value")
        else:
            name = pos.instrument.name[:col_w[0]]
            shares = pos.volume.value if pos.volume else None
            invested = pos.acquiredValue.value if pos.acquiredValue else None
            value = pos.value.value if pos.value else None
            day_pct = (pos.lastTradingDayPerformance.relative.value
                       if pos.lastTradingDayPerformance and pos.lastTradingDayPerformance.relative else None)

        gain_sek = None
        gain_pct = None
        if value is not None and invested is not None:
            gain_sek = value - invested
            gain_pct = (gain_sek / invested * 100) if invested != 0 else 0.0

        if invested:
            total_invested += invested
        if value:
            total_value += value
        if gain_sek:
            total_gain += gain_sek

        gain_str = fmt(gain_sek)
        gain_pct_str = f"{fmt(gain_pct, 1)}%" if gain_pct is not None else "—"
        day_str = f"{fmt(day_pct, 1)}%" if day_pct is not None else "—"
        shares_str = fmt(shares, 0) if shares and shares == int(shares) else fmt(shares)

        print(
            f"{name:<{col_w[0]}}  {shares_str:>{col_w[1]}}  "
            f"{fmt(invested):>{col_w[2]}}  {fmt(value):>{col_w[3]}}  "
            f"{gain_str:>{col_w[4]}}  {gain_pct_str:>{col_w[5]}}  {day_str:>{col_w[6]}}"
        )

    print(sep)
    total_gain_pct = (total_gain / total_invested * 100) if total_invested else 0
    print(
        f"{'TOTAL':<{col_w[0]}}  {'':>{col_w[1]}}  "
        f"{fmt(total_invested):>{col_w[2]}}  {fmt(total_value):>{col_w[3]}}  "
        f"{fmt(total_gain):>{col_w[4]}}  {fmt(total_gain_pct, 1) + '%':>{col_w[5]}}"
    )

    # Cash positions
    if cash_positions:
        print("\n## Cash Positions\n")
        for cash in cash_positions:
            if isinstance(cash, dict):
                acc_name = gv(cash, "account", "name") or gv(cash, "account", "id") or "—"
                balance = gv(cash, "totalBalance", "value")
                unit = gv(cash, "totalBalance", "unit") or "SEK"
            else:
                acc_name = cash.account.name if hasattr(cash.account, "name") else cash.account.id
                balance = cash.totalBalance.value if cash.totalBalance else None
                unit = cash.totalBalance.unit if cash.totalBalance else "SEK"
            print(f"  {acc_name}: {fmt(balance)} {unit}")


if __name__ == "__main__":
    main()

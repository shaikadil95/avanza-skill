# /// script
# dependencies = ["avanza-api"]
# ///
"""
Portfolio insights report: total development, best/worst performers, dividends.

Usage: uv run insights.py [period]
Periods: today | week | ytd (default) | 3y
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


PERIOD_MAP = {
    "today": "TODAY",
    "week":  "ONE_WEEK",
    "ytd":   "THIS_YEAR",
    "3y":    "THREE_YEARS_ROLLING",
}

PERIOD_LABELS = {
    "TODAY":               "Today",
    "ONE_WEEK":            "Last 7 days",
    "THIS_YEAR":           "Year-to-date",
    "THREE_YEARS_ROLLING": "3-year rolling",
}


def main():
    check_credentials()

    period_arg = (sys.argv[1] if len(sys.argv) > 1 else "ytd").lower()
    if period_arg not in PERIOD_MAP:
        print(f"ERROR: Unknown period '{period_arg}'. Choose: {', '.join(PERIOD_MAP)}", file=sys.stderr)
        sys.exit(1)

    period_key = PERIOD_MAP[period_arg]

    from avanza import Avanza, InsightsReportTimePeriod

    avanza = Avanza({
        "username": os.environ["AVANZA_USERNAME"],
        "password": os.environ["AVANZA_PASSWORD"],
        "totpSecret": os.environ["AVANZA_TOTP_SECRET"],
    })

    # Collect account IDs from overview
    overview = avanza.get_overview()
    account_ids = [acc.id for acc in overview.accounts if acc.id]

    if not account_ids:
        print("ERROR: No accounts found.", file=sys.stderr)
        sys.exit(1)

    period_enum = InsightsReportTimePeriod[period_key]
    report = avanza.get_insights_report(
        account_ids=account_ids,
        time_period=period_enum,
    )

    label = PERIOD_LABELS.get(period_key, period_arg)
    print(f"## Portfolio Insights — {label}\n")

    # --- Overall development ---
    td = report.totalDevelopment
    if td:
        period_from = getattr(report, "from", None) or getattr(report, "from_", None)
        period_to = getattr(report, "to", None)
        if period_from and period_to:
            print(f"Period: {period_from} → {period_to}\n")

        start = getattr(td, "startingValue", None)
        end = getattr(td, "endValue", None)
        change = getattr(td, "totalChange", None)
        change_pct = getattr(td, "totalChangePercent", None)

        print("### Overall Development\n")
        print(f"  Start value : {fmt(start)} SEK")
        print(f"  End value   : {fmt(end)} SEK")
        change_str = fmt(change)
        pct_str = f"{fmt(change_pct, 2)}%" if change_pct is not None else "—"
        print(f"  Total gain  : {change_str} SEK  ({pct_str})")

    # --- Breakdown: development vs dividends ---
    dr = report.developmentResponse
    if dr and dr.totalOutcome:
        out = dr.totalOutcome
        dev = getattr(out, "development", None)
        div = getattr(out, "dividends", None)
        total = getattr(out, "total", None)
        print("\n### Breakdown\n")
        print(f"  Price appreciation : {fmt(dev)} SEK")
        print(f"  Dividends          : {fmt(div)} SEK")
        print(f"  Combined total     : {fmt(total)} SEK")

    # --- Best performers ---
    if dr and dr.bestAndWorst:
        bw = dr.bestAndWorst
        best = getattr(bw, "bestPositions", []) or []
        worst = getattr(bw, "worstPositions", []) or []

        if best:
            print("\n### Best Performers\n")
            col_w = [24, 14, 10, 14]
            header = f"{'Stock':<{col_w[0]}} {'Gain (SEK)':>{col_w[1]}} {'Return %':>{col_w[2]}} {'End Value':>{col_w[3]}}"
            sep = "  ".join("-" * w for w in col_w)
            print(header)
            print(sep)
            for pos in best[:5]:
                name = (pos.name or "—")[:col_w[0]]
                dev_val = getattr(pos, "development", None)
                pct = getattr(pos, "totalDevelopmentInPercent", None)
                ev = getattr(pos, "endValue", None)
                pct_str = f"{fmt(pct, 1)}%" if pct is not None else "—"
                print(f"{name:<{col_w[0]}}  {fmt(dev_val):>{col_w[1]}}  {pct_str:>{col_w[2]}}  {fmt(ev):>{col_w[3]}}")

        if worst:
            print("\n### Worst Performers\n")
            print(header)
            print(sep)
            for pos in worst[:5]:
                name = (pos.name or "—")[:col_w[0]]
                dev_val = getattr(pos, "development", None)
                pct = getattr(pos, "totalDevelopmentInPercent", None)
                ev = getattr(pos, "endValue", None)
                pct_str = f"{fmt(pct, 1)}%" if pct is not None else "—"
                print(f"{name:<{col_w[0]}}  {fmt(dev_val):>{col_w[1]}}  {pct_str:>{col_w[2]}}  {fmt(ev):>{col_w[3]}}")


if __name__ == "__main__":
    main()

# /// script
# dependencies = ["avanza-api"]
# ///
"""
Portfolio vs benchmark comparison.

Usage: uv run compare.py [period]
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


def gv(d, *keys, default=None):
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
        if d is default:
            return default
    return d


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

# Field in historicalClosingPrices that corresponds to each period
HIST_FIELD = {
    "TODAY":               "oneDay",
    "ONE_WEEK":            "oneWeek",
    "THIS_YEAR":           "startOfYear",
    "THREE_YEARS_ROLLING": "threeYears",
}

# Avanza orderbookIds for Swedish benchmark indices
BENCHMARKS = [
    ("OMXS30",  "19002"),
    ("OMXSPI",  "51268"),
]


def main():
    check_credentials()

    period_arg = (sys.argv[1] if len(sys.argv) > 1 else "ytd").lower()
    if period_arg not in PERIOD_MAP:
        print(f"ERROR: Unknown period '{period_arg}'. Choose: {', '.join(PERIOD_MAP)}", file=sys.stderr)
        sys.exit(1)

    period_key = PERIOD_MAP[period_arg]
    hist_field = HIST_FIELD[period_key]

    from avanza import Avanza
    from avanza.constants import InsightsReportTimePeriod

    avanza = Avanza({
        "username": os.environ["AVANZA_USERNAME"],
        "password": os.environ["AVANZA_PASSWORD"],
        "totpSecret": os.environ["AVANZA_TOTP_SECRET"],
    }, retry_with_next_otp=True)

    # Portfolio performance via insights report
    overview = avanza.get_overview()
    if isinstance(overview, dict):
        accounts = overview.get("accounts", [])
        account_ids = [acc.get("id") for acc in accounts if acc.get("id")]
    else:
        account_ids = [acc.id for acc in overview.accounts if acc.id]
        account_ids = [a for a in account_ids if a]

    if not account_ids:
        print("ERROR: No accounts found.", file=sys.stderr)
        sys.exit(1)

    period_enum = InsightsReportTimePeriod[period_key]
    # API accepts comma-separated account IDs for multi-account portfolios
    report = avanza.get_insights_report(account_id=",".join(account_ids), time_period=period_enum)

    if isinstance(report, dict):
        td = report.get("totalDevelopment") or {}
        period_from = report.get("from") or report.get("from_") or "—"
        period_to = report.get("to") or "—"
        if isinstance(td, dict):
            start = td.get("startingValue") or td.get("startValue")
            change = td.get("totalChange")
            change_pct = td.get("totalChangePercent")
        else:
            start = getattr(td, "startingValue", None) or getattr(td, "startValue", None)
            change = getattr(td, "totalChange", None)
            change_pct = getattr(td, "totalChangePercent", None)
    else:
        td = getattr(report, "totalDevelopment", None)
        period_from = getattr(report, "from_", None) or getattr(report, "from", None) or "—"
        period_to = getattr(report, "to", None) or "—"
        start = getattr(td, "startingValue", None) or getattr(td, "startValue", None) if td else None
        change = getattr(td, "totalChange", None) if td else None
        change_pct = getattr(td, "totalChangePercent", None) if td else None

    if change_pct is None and start and change:
        change_pct = change / start * 100

    label = PERIOD_LABELS.get(period_key, period_arg)
    print(f"## Portfolio vs Benchmarks — {label}\n")
    print(f"Period: {period_from} → {period_to}\n")

    col_w = [20, 12, 14]
    sep = "  ".join("-" * w for w in col_w)

    def pct_str(v):
        if v is None:
            return "—"
        return f"{'+' if v >= 0 else ''}{fmt(v, 2)}%"

    # Portfolio line (header row)
    print(f"{'Portfolio':<{col_w[0]}}  {pct_str(change_pct):>{col_w[1]}}  {'—':>{col_w[2]}}")
    print(sep)
    print(f"{'Benchmark':<{col_w[0]}} {'Return %':>{col_w[1]}} {'Vs Portfolio':>{col_w[2]}}")
    print(sep)

    # Benchmark rows
    for bench_name, ob_id in BENCHMARKS:
        try:
            idx = avanza.get_index_info(ob_id)
            if isinstance(idx, dict):
                hist = idx.get("historicalClosingPrices") or {}
                bench_pct = hist.get(hist_field) if isinstance(hist, dict) else getattr(hist, hist_field, None)
            else:
                hist = getattr(idx, "historicalClosingPrices", None)
                bench_pct = getattr(hist, hist_field, None) if hist else None

            if bench_pct is not None and change_pct is not None:
                delta = change_pct - bench_pct
                delta_str = pct_str(delta)
            else:
                delta_str = "—"

            bench_str = pct_str(bench_pct)
        except Exception:
            bench_str = "n/a"
            delta_str = "—"

        print(f"{bench_name:<{col_w[0]}}  {bench_str:>{col_w[1]}}  {delta_str:>{col_w[2]}}")

    print(sep)
    print("\nNote: Index returns are point-to-point closing prices, not FX-adjusted.")


if __name__ == "__main__":
    main()

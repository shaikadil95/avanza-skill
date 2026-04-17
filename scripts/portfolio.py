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


def main():
    check_credentials()

    from avanza import Avanza

    avanza = Avanza({
        "username": os.environ["AVANZA_USERNAME"],
        "password": os.environ["AVANZA_PASSWORD"],
        "totpSecret": os.environ["AVANZA_TOTP_SECRET"],
    })

    overview = avanza.get_overview()

    print("## Portfolio Overview\n")

    col_w = [28, 14, 14, 14, 10]
    header = f"{'Account':<{col_w[0]}} {'Balance':>{col_w[1]}} {'Total Value':>{col_w[2]}} {'Profit':>{col_w[3]}} {'Return':>{col_w[4]}}"
    sep = "  ".join("-" * w for w in col_w)
    print(header)
    print(sep)

    total_value = 0.0
    total_profit = 0.0

    for acc in overview.accounts:
        name = (acc.name.userDefinedName or acc.name.defaultName)[:col_w[0]]
        balance = acc.balance.value if acc.balance else None
        total_val = acc.totalValue.value if acc.totalValue else None
        profit = acc.profit.absolute.value if acc.profit and acc.profit.absolute else None
        ret = acc.profit.relative.value if acc.profit and acc.profit.relative else None
        unit = acc.totalValue.unit if acc.totalValue else "SEK"

        if total_val:
            total_value += total_val
        if profit:
            total_profit += profit

        ret_str = f"{fmt(ret, 1)}%" if ret is not None else "—"
        print(
            f"{name:<{col_w[0]}}  {fmt(balance):>{col_w[1]}}  {fmt(total_val):>{col_w[2]}}  {fmt(profit):>{col_w[3]}}  {ret_str:>{col_w[4]}}"
        )

    print(sep)
    print(f"{'TOTAL':<{col_w[0]}}  {'':>{col_w[1]}}  {fmt(total_value):>{col_w[2]}}  {fmt(total_profit):>{col_w[3]}}")


if __name__ == "__main__":
    main()

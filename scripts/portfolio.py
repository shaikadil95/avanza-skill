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


def get_nested(d, *keys, default=None):
    """Safely traverse nested dicts."""
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

    overview = avanza.get_overview()

    print("## Portfolio Overview\n")

    col_w = [28, 14, 14, 14, 10]
    header = f"{'Account':<{col_w[0]}} {'Balance':>{col_w[1]}} {'Total Value':>{col_w[2]}} {'Profit':>{col_w[3]}} {'Return':>{col_w[4]}}"
    sep = "  ".join("-" * w for w in col_w)
    print(header)
    print(sep)

    total_value = 0.0
    total_profit = 0.0

    accounts = overview.get("accounts", []) if isinstance(overview, dict) else overview.accounts

    for acc in accounts:
        if isinstance(acc, dict):
            name_obj = acc.get("name", {})
            name = (name_obj.get("userDefinedName") or name_obj.get("defaultName") or acc.get("id", "Unknown"))[:col_w[0]]
            balance = get_nested(acc, "balance", "value")
            total_val = get_nested(acc, "totalValue", "value")
            profit = get_nested(acc, "profit", "absolute", "value")
            ret = get_nested(acc, "profit", "relative", "value")
            acc_type = acc.get("type", "")
        else:
            name = (acc.name.userDefinedName or acc.name.defaultName)[:col_w[0]]
            balance = acc.balance.value if acc.balance else None
            total_val = acc.totalValue.value if acc.totalValue else None
            profit = acc.profit.absolute.value if acc.profit and acc.profit.absolute else None
            ret = acc.profit.relative.value if acc.profit and acc.profit.relative else None
            acc_type = getattr(acc, "type", "")

        if total_val:
            total_value += total_val
        if profit:
            total_profit += profit

        # Append account type abbreviation for clarity
        type_abbrev = {
            "INVESTERINGSSPARKONTO": "ISK",
            "AKTIEFONDKONTO": "AF",
            "AKTIE_FOND_KONTO": "AF",
            "KAPITALFORSAKRING": "KF",
        }.get(acc_type, acc_type[:3] if acc_type else "")
        display_name = f"{name} ({type_abbrev})" if type_abbrev else name
        display_name = display_name[:col_w[0]]

        ret_str = f"{fmt(ret, 1)}%" if ret is not None else "—"
        print(
            f"{display_name:<{col_w[0]}}  {fmt(balance):>{col_w[1]}}  {fmt(total_val):>{col_w[2]}}  {fmt(profit):>{col_w[3]}}  {ret_str:>{col_w[4]}}"
        )

    print(sep)
    print(f"{'TOTAL':<{col_w[0]}}  {'':>{col_w[1]}}  {fmt(total_value):>{col_w[2]}}  {fmt(total_profit):>{col_w[3]}}")


if __name__ == "__main__":
    main()

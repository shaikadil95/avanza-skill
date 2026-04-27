# /// script
# dependencies = ["avanza-api"]
# ///
"""
Multi-timeframe swing trade analysis (weekly / daily / 4H).

Indicators : MACD, Stochastic, Bollinger Bands, Volume
Scoring    : per Multi-Timeframe Technical Convergence model
Fusion     : weekly defines direction, daily confirms, 4H times entry

Usage: uv run swing_trade.py <name_or_ticker_or_isin>
"""

import math
import os
import sys


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def check_credentials():
    missing = [v for v in ("AVANZA_USERNAME", "AVANZA_PASSWORD", "AVANZA_TOTP_SECRET") if not os.getenv(v)]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Run: export AVANZA_USERNAME=... AVANZA_PASSWORD=... AVANZA_TOTP_SECRET=...", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Technical indicators  (pure Python, no extra dependencies)
# ---------------------------------------------------------------------------

def _ema_series(values, period):
    if not values:
        return []
    alpha = 2.0 / (period + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])
    return result


def compute_macd(closes, fast=12, slow=26, signal=9):
    """Returns (macd_val, signal_val, histogram) or (None, None, None)."""
    if len(closes) < slow + signal:
        return None, None, None
    fast_ema = _ema_series(closes, fast)
    slow_ema = _ema_series(closes, slow)
    macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
    signal_ema = _ema_series(macd_line, signal)
    macd_val = macd_line[-1]
    sig_val = signal_ema[-1]
    return macd_val, sig_val, macd_val - sig_val


def compute_stochastic(highs, lows, closes, k_period=14, d_period=3):
    """Returns (%K, %D) or (None, None)."""
    if len(closes) < k_period + d_period - 1:
        return None, None
    n = len(closes)
    k_vals = []
    for i in range(n - d_period, n):
        start = max(0, i - k_period + 1)
        h = max(highs[start:i + 1])
        l = min(lows[start:i + 1])
        k_vals.append(100.0 * (closes[i] - l) / (h - l) if h != l else 50.0)
    return k_vals[-1], sum(k_vals) / d_period


def compute_bollinger(closes, period=20, mult=2.0):
    """Returns (upper, middle, lower, band_width_pct) or (None, None, None, None)."""
    if len(closes) < period:
        return None, None, None, None
    window = closes[-period:]
    mid = sum(window) / period
    variance = sum((x - mid) ** 2 for x in window) / period
    std = math.sqrt(variance)
    upper = mid + mult * std
    lower = mid - mult * std
    bw = (upper - lower) / mid * 100 if mid != 0 else 0.0
    return upper, mid, lower, bw


def analyze_volume(volumes, period=20):
    """Returns ('strong'|'weak'|'neutral', ratio)."""
    if len(volumes) < period + 1:
        return "neutral", 1.0
    ma = sum(volumes[-(period + 1):-1]) / period
    if ma <= 0:
        return "neutral", 1.0
    ratio = volumes[-1] / ma
    if ratio >= 1.2:
        return "strong", ratio
    if ratio <= 0.8:
        return "weak", ratio
    return "neutral", ratio


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def extract_ohlcv(ohlc_list):
    """Returns (opens, highs, lows, closes, volumes) as float lists."""
    if not ohlc_list:
        return [], [], [], [], []
    if isinstance(ohlc_list[0], dict):
        opens   = [c.get("open",  0.0) for c in ohlc_list]
        highs   = [c.get("high",  0.0) for c in ohlc_list]
        lows    = [c.get("low",   0.0) for c in ohlc_list]
        closes  = [c.get("close", 0.0) for c in ohlc_list]
        volumes = [c.get("totalVolumeTraded", 0) for c in ohlc_list]
    else:
        opens   = [c.open for c in ohlc_list]
        highs   = [c.high for c in ohlc_list]
        lows    = [c.low  for c in ohlc_list]
        closes  = [c.close for c in ohlc_list]
        volumes = [c.totalVolumeTraded for c in ohlc_list]
    return opens, highs, lows, closes, volumes


def aggregate_to_4h(hourly_ohlc):
    """Group consecutive hourly candles into 4-hour candles."""
    result = []
    i = 0
    while i + 3 < len(hourly_ohlc):
        group = hourly_ohlc[i:i + 4]
        if isinstance(group[0], dict):
            result.append({
                "timestamp": group[0]["timestamp"],
                "open":  group[0]["open"],
                "close": group[-1]["close"],
                "high":  max(c["high"] for c in group),
                "low":   min(c["low"]  for c in group),
                "totalVolumeTraded": sum(c.get("totalVolumeTraded", 0) for c in group),
            })
        else:
            result.append({
                "timestamp": group[0].timestamp,
                "open":  group[0].open,
                "close": group[-1].close,
                "high":  max(c.high for c in group),
                "low":   min(c.low  for c in group),
                "totalVolumeTraded": sum(c.totalVolumeTraded for c in group),
            })
        i += 4
    return result


def extract_orderbook_id(hit):
    """Extract the numeric orderbookId from a search result.

    Avanza returns `orderBookId` directly for US-listed stocks (path is None).
    For Swedish listings the ID is embedded in the path as the last numeric segment.
    """
    # Prefer the top-level orderBookId field (present for NYSE/NASDAQ stocks)
    ob_id = hit.get("orderBookId") or hit.get("orderbookId")
    if ob_id:
        return str(ob_id)
    # Fall back to parsing the path for Swedish-listed stocks
    path = hit.get("path", "") or ""
    for part in reversed(path.split("/")):
        try:
            int(part)
            return part
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Signal interpretation
# ---------------------------------------------------------------------------

def interpret_macd(macd_val, signal_val, hist):
    if macd_val is None or signal_val is None:
        return "neutral"
    if macd_val > signal_val:
        return "bullish"
    if macd_val < signal_val:
        return "bearish"
    return "neutral"


def interpret_bb(close, bb_upper, bb_mid, bb_lower):
    if close is None or bb_mid is None:
        return "neutral"
    if close > bb_upper:
        return "bullish"
    if close < bb_lower:
        return "bearish"
    return "bullish" if close > bb_mid else "bearish"


def interpret_stochastic(k, d):
    if k is None:
        return "neutral"
    if k < 20 and (d is None or k >= d):
        return "bullish"
    if k > 80 and (d is None or k <= d):
        return "bearish"
    if d is not None:
        return "bullish" if k > d else "bearish"
    return "neutral"


def determine_trend(macd_val, signal_val, hist, close, bb_upper, bb_mid, bb_lower):
    """Combine MACD (primary) + Bollinger (confirms) into a single trend label."""
    macd_sig = interpret_macd(macd_val, signal_val, hist)
    bb_sig   = interpret_bb(close, bb_upper, bb_mid, bb_lower)
    if macd_sig == "bullish" and bb_sig == "bullish":
        return "bullish"
    if macd_sig == "bearish" and bb_sig == "bearish":
        return "bearish"
    if macd_sig != "neutral":
        return macd_sig
    if bb_sig != "neutral":
        return bb_sig
    return "neutral"


# ---------------------------------------------------------------------------
# Scoring model
# ---------------------------------------------------------------------------

def score_weekly(macd_val, signal_val, close, bb_mid, vol_status):
    s = 0.0
    if macd_val is not None and signal_val is not None:
        s += 2.0 if macd_val > signal_val else -2.0
    if close is not None and bb_mid is not None:
        s += 1.0 if close > bb_mid else -1.0
    s += 2.0 if vol_status == "strong" else (-3.0 if vol_status == "weak" else 0.0)
    return s * 2.0  # 2x timeframe weight


def score_daily(macd_val, signal_val, k, d, close, bb_mid, vol_status):
    s = 0.0
    if macd_val is not None and signal_val is not None:
        s += 1.5 if macd_val > signal_val else -1.5
    stoch = interpret_stochastic(k, d)
    s += 1.0 if stoch == "bullish" else (-1.0 if stoch == "bearish" else 0.0)
    if close is not None and bb_mid is not None:
        s += 1.0 if close > bb_mid else -1.0
    s += 2.0 if vol_status == "strong" else (-3.0 if vol_status == "weak" else 0.0)
    return s * 1.5  # 1.5x timeframe weight


def score_h4(k, d, close, bb_mid, vol_status):
    s = 0.0
    stoch = interpret_stochastic(k, d)
    s += 1.0 if stoch == "bullish" else (-1.0 if stoch == "bearish" else 0.0)
    if close is not None and bb_mid is not None:
        s += 1.0 if close > bb_mid else -1.0
    s += 1.0 if vol_status == "strong" else (-2.0 if vol_status == "weak" else 0.0)
    return s * 1.0  # 1x timeframe weight


# ---------------------------------------------------------------------------
# Fusion logic
# ---------------------------------------------------------------------------

def apply_fusion(w_trend, d_trend, h4_trend, w_vol, d_vol, h4_vol):
    """Returns (strategy, global_bias) per the convergence ruleset."""
    if (w_vol == "weak" and d_vol == "weak") or (w_trend == "neutral" and d_trend == "neutral"):
        return "no_trade", "neutral"

    if w_trend == "bullish" and d_trend == "bullish" and d_vol == "strong":
        return "trend_following", "bullish"
    if w_trend == "bearish" and d_trend == "bearish" and d_vol == "strong":
        return "trend_following", "bearish"

    if w_trend == "bullish" and d_trend in ("neutral", "bearish") and h4_trend == "bullish":
        return "pullback_entry", "bullish"
    if w_trend == "bearish" and d_trend in ("neutral", "bullish") and h4_trend == "bearish":
        return "pullback_entry", "bearish"

    if w_trend == "bullish" and d_trend == "bullish":
        return "trend_following", "bullish"
    if w_trend == "bearish" and d_trend == "bearish":
        return "trend_following", "bearish"

    if w_trend == "bearish" and d_vol == "strong":
        return "reversal", "bearish"

    if w_trend == "bullish":
        return "pullback_entry", "bullish"
    if w_trend == "bearish":
        return "reversal", "bearish"

    return "no_trade", "neutral"


def compute_confidence(strategy, w_trend, d_trend, h4_trend, w_vol, d_vol):
    if strategy == "no_trade":
        return 0
    vol_ok = w_vol == "strong" or d_vol == "strong"
    if strategy == "trend_following":
        if w_trend == d_trend == h4_trend and vol_ok:
            return 3
        if w_trend == d_trend and vol_ok:
            return 2
        return 1
    if strategy == "pullback_entry":
        return 2 if vol_ok else 1
    if strategy == "reversal":
        return 2 if vol_ok else 1
    return 0


# ---------------------------------------------------------------------------
# Trade plan
# ---------------------------------------------------------------------------

def compute_trade_plan(bias, close, bb_upper, bb_lower, daily_lows, daily_highs):
    if bias == "neutral" or close is None:
        return None, None, None

    if bias == "bullish":
        entry = (round(close * 0.995, 2), round(close * 1.005, 2))
        sw_low = min(daily_lows[-5:]) if len(daily_lows) >= 5 else None
        if sw_low is not None and bb_lower is not None:
            stop = max(sw_low, bb_lower)
        else:
            stop = sw_low or bb_lower or close * 0.97
        risk = max(close - stop, close * 0.005)
        return entry, round(stop, 2), round(close + 2 * risk, 2)

    entry = (round(close * 0.995, 2), round(close * 1.005, 2))
    sw_high = max(daily_highs[-5:]) if len(daily_highs) >= 5 else None
    if sw_high is not None and bb_upper is not None:
        stop = min(sw_high, bb_upper)
    else:
        stop = sw_high or bb_upper or close * 1.03
    risk = max(stop - close, close * 0.005)
    return entry, round(stop, 2), round(close - 2 * risk, 2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    check_credentials()

    if len(sys.argv) < 2:
        print("Usage: swing_trade.py <name_or_ticker_or_isin>", file=sys.stderr)
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    from avanza import Avanza
    from avanza.constants import TimePeriod, Resolution

    avanza = Avanza({
        "username": os.environ["AVANZA_USERNAME"],
        "password": os.environ["AVANZA_PASSWORD"],
        "totpSecret": os.environ["AVANZA_TOTP_SECRET"],
    }, retry_with_next_otp=True)

    # --- Resolve stock ---
    hits = avanza.search_for_stock(query, limit=5)
    if not hits:
        print(f"ERROR: No stocks found matching '{query}'.", file=sys.stderr)
        sys.exit(1)

    hit = hits[0] if isinstance(hits[0], dict) else vars(hits[0])
    stock_name = hit.get("title", query)
    ob_id = extract_orderbook_id(hit)
    if not ob_id:
        print(f"ERROR: Could not resolve orderbookId for '{stock_name}'.", file=sys.stderr)
        sys.exit(1)

    # --- Fetch chart data ---
    def fetch_ohlc(period, resolution):
        try:
            data = avanza.get_chart_data(ob_id, period, resolution)
            return (data.get("ohlc", []) if isinstance(data, dict)
                    else getattr(data, "ohlc", []))
        except Exception:
            return []

    weekly_ohlc = fetch_ohlc(TimePeriod.ONE_YEAR,     Resolution.WEEK)
    daily_ohlc  = fetch_ohlc(TimePeriod.THREE_MONTHS, Resolution.DAY)
    hourly_ohlc = fetch_ohlc(TimePeriod.ONE_MONTH,    Resolution.HOUR)
    h4_ohlc     = aggregate_to_4h(hourly_ohlc)

    if not weekly_ohlc or not daily_ohlc:
        print("ERROR: Insufficient chart data for analysis.", file=sys.stderr)
        sys.exit(1)

    # --- Extract OHLCV ---
    _, w_highs, w_lows, w_closes, w_vols = extract_ohlcv(weekly_ohlc)
    _, d_highs, d_lows, d_closes, d_vols = extract_ohlcv(daily_ohlc)
    _, h4_highs, h4_lows, h4_closes, h4_vols = extract_ohlcv(h4_ohlc)

    # --- Indicators ---
    w_macd, w_sig, w_hist = compute_macd(w_closes)
    w_bb_u, w_bb_m, w_bb_l, _ = compute_bollinger(w_closes)
    w_vol, w_vol_r = analyze_volume(w_vols)
    w_close = w_closes[-1] if w_closes else None

    d_macd, d_sig, d_hist = compute_macd(d_closes)
    d_k, d_d = compute_stochastic(d_highs, d_lows, d_closes)
    d_bb_u, d_bb_m, d_bb_l, _ = compute_bollinger(d_closes)
    d_vol, d_vol_r = analyze_volume(d_vols)
    d_close = d_closes[-1] if d_closes else None

    if h4_closes:
        h4_macd, h4_sig, h4_hist = compute_macd(h4_closes)
        h4_k, h4_d = compute_stochastic(h4_highs, h4_lows, h4_closes)
        h4_bb_u, h4_bb_m, h4_bb_l, _ = compute_bollinger(h4_closes)
        h4_vol, h4_vol_r = analyze_volume(h4_vols)
        h4_close = h4_closes[-1]
    else:
        h4_macd = h4_sig = h4_hist = None
        h4_k = h4_d = None
        h4_bb_u = h4_bb_m = h4_bb_l = None
        h4_vol, h4_vol_r = "neutral", 1.0
        h4_close = None

    # --- Trends ---
    w_trend  = determine_trend(w_macd,  w_sig,  w_hist,  w_close,  w_bb_u,  w_bb_m,  w_bb_l)
    d_trend  = determine_trend(d_macd,  d_sig,  d_hist,  d_close,  d_bb_u,  d_bb_m,  d_bb_l)
    h4_trend = determine_trend(h4_macd, h4_sig, h4_hist, h4_close, h4_bb_u, h4_bb_m, h4_bb_l)

    # --- Scores ---
    ws = score_weekly(w_macd, w_sig, w_close, w_bb_m, w_vol)
    ds = score_daily(d_macd, d_sig, d_k, d_d, d_close, d_bb_m, d_vol)
    hs = score_h4(h4_k, h4_d, h4_close, h4_bb_m, h4_vol)
    total = ws + ds + hs

    W_MAX = (2 + 1 + 2) * 2        # 10.0
    D_MAX = (1.5 + 1 + 1 + 2) * 1.5  # 8.25
    H_MAX = (1 + 1 + 1) * 1          # 3.0

    # --- Fusion ---
    strategy, bias = apply_fusion(w_trend, d_trend, h4_trend, w_vol, d_vol, h4_vol)
    confidence = compute_confidence(strategy, w_trend, d_trend, h4_trend, w_vol, d_vol)
    validity = "valid" if confidence >= 1 else "invalid"

    # --- Trade plan ---
    entry, stop_loss, take_profit = compute_trade_plan(
        bias, d_close, d_bb_u, d_bb_l, d_lows, d_highs
    )

    # -----------------------------------------------------------------------
    # Output
    # -----------------------------------------------------------------------

    TSYM = {"bullish": "bullish", "bearish": "bearish", "neutral": "neutral"}

    W, C1, C2, C3 = 18, 12, 12, 12
    hdr = f"{'':>{W}}  {'Weekly':>{C1}}  {'Daily':>{C2}}  {'4H':>{C3}}"
    sep = f"{'':>{W}}  {'-'*C1}  {'-'*C2}  {'-'*C3}"

    def row(label, w_v, d_v, h_v):
        print(f"  {label:<{W}}  {w_v:>{C1}}  {d_v:>{C2}}  {h_v:>{C3}}")

    print(f"## Swing Trade Analysis — {stock_name}\n")
    print(f"orderbookId: {ob_id}  |  "
          f"Data: {len(w_closes)}W / {len(d_closes)}D / {len(h4_closes)} 4H bars\n")

    print("### Timeframe Alignment\n")
    print(hdr)
    print(sep)
    row("Trend",
        TSYM[w_trend], TSYM[d_trend], TSYM[h4_trend])
    row("MACD",
        interpret_macd(w_macd, w_sig, w_hist),
        interpret_macd(d_macd, d_sig, d_hist),
        interpret_macd(h4_macd, h4_sig, h4_hist))
    row("Stochastic",
        "—",
        interpret_stochastic(d_k, d_d),
        interpret_stochastic(h4_k, h4_d))
    row("Bollinger",
        interpret_bb(w_close, w_bb_u, w_bb_m, w_bb_l),
        interpret_bb(d_close, d_bb_u, d_bb_m, d_bb_l),
        interpret_bb(h4_close, h4_bb_u, h4_bb_m, h4_bb_l))
    row("Volume",
        w_vol, d_vol, h4_vol)
    print()

    print("### Scores\n")
    print(f"  Weekly   : {fmt(ws):>7}  / {W_MAX:.1f}  (2x weight)")
    print(f"  Daily    : {fmt(ds):>7}  / {D_MAX:.2f}  (1.5x weight)")
    print(f"  4H       : {fmt(hs):>7}  / {H_MAX:.1f}  (1x weight)")
    print(f"  {'':->33}")
    print(f"  Total    : {fmt(total):>7}  / {W_MAX + D_MAX + H_MAX:.2f}")
    print()

    print("### Analysis\n")
    print(f"  Global bias   : {bias}")
    print(f"  Strategy      : {strategy.replace('_', ' ')}")
    print(f"  Confidence    : {confidence} / 3")
    print(f"  Validity      : {validity}")
    print()

    print("### Indicator Values\n")
    print(f"  {'':16}  {'Weekly':>12}  {'Daily':>12}  {'4H':>12}")
    print(f"  {'':16}  {'--------':>12}  {'--------':>12}  {'--------':>12}")
    print(f"  {'MACD line':16}  {fmt(w_macd):>12}  {fmt(d_macd):>12}  {fmt(h4_macd):>12}")
    print(f"  {'MACD signal':16}  {fmt(w_sig):>12}  {fmt(d_sig):>12}  {fmt(h4_sig):>12}")
    print(f"  {'BB upper':16}  {fmt(w_bb_u):>12}  {fmt(d_bb_u):>12}  {fmt(h4_bb_u):>12}")
    print(f"  {'BB middle':16}  {fmt(w_bb_m):>12}  {fmt(d_bb_m):>12}  {fmt(h4_bb_m):>12}")
    print(f"  {'BB lower':16}  {fmt(w_bb_l):>12}  {fmt(d_bb_l):>12}  {fmt(h4_bb_l):>12}")
    stoch_str = lambda k, d: f"{fmt(k, 1)}% / {fmt(d, 1)}%" if k is not None else "—"
    print(f"  {'Stoch K / D':16}  {'—':>12}  {stoch_str(d_k, d_d):>12}  {stoch_str(h4_k, h4_d):>12}")
    print(f"  {'Close':16}  {fmt(w_close):>12}  {fmt(d_close):>12}  {fmt(h4_close):>12}")
    print(f"  {'Vol ratio':16}  {fmt(w_vol_r, 2)+'x':>12}  {fmt(d_vol_r, 2)+'x':>12}  {fmt(h4_vol_r, 2)+'x':>12}")
    print()

    print("### Trade Plan\n")
    if validity == "valid" and entry is not None:
        direction = "LONG" if bias == "bullish" else "SHORT"
        risk = abs(entry[0] - stop_loss) if stop_loss is not None else None
        print(f"  Direction      : {direction}")
        print(f"  Entry zone     : {fmt(entry[0])} – {fmt(entry[1])}")
        if stop_loss is not None:
            print(f"  Stop loss      : {fmt(stop_loss)}"
                  + (f"  (risk ~{fmt(risk)} per share)" if risk else ""))
        if take_profit is not None:
            print(f"  Take profit    : {fmt(take_profit)}  (R:R 1:2)")
        print()
        print("  Prices in Avanza listing currency. Apply your own risk management.")
    else:
        print("  No trade signal — mixed signals or insufficient volume confirmation.")

    print()
    print("Note: Weekly is non-negotiable. If weekly and daily disagree, no trade.")
    print("      4H is entry timing only. Volume is the final gatekeeper.")


if __name__ == "__main__":
    main()

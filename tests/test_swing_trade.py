import sys
from unittest.mock import patch

import pytest

from tests.conftest import (
    MOCK_CHART_DAILY,
    MOCK_CHART_HOURLY,
    MOCK_CHART_WEEKLY,
    MOCK_SEARCH_HITS,
    load_script,
)


def _run(monkeypatch, query="APPLE", weekly=None, daily=None, hourly=None, hits=None):
    monkeypatch.setattr(sys, "argv", ["swing_trade.py", query])
    with patch("avanza.Avanza") as MockAvanza:
        inst = MockAvanza.return_value
        inst.search_for_stock.return_value = hits if hits is not None else MOCK_SEARCH_HITS
        inst.get_chart_data.side_effect = [
            weekly  if weekly  is not None else MOCK_CHART_WEEKLY,
            daily   if daily   is not None else MOCK_CHART_DAILY,
            hourly  if hourly  is not None else MOCK_CHART_HOURLY,
        ]
        load_script("swing_trade").main()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_header_shows_stock_name(monkeypatch, capsys):
    _run(monkeypatch)
    assert "APPLE INC" in capsys.readouterr().out


def test_orderbook_id_extracted(monkeypatch, capsys):
    _run(monkeypatch)
    assert "5447" in capsys.readouterr().out


def test_timeframe_alignment_section(monkeypatch, capsys):
    _run(monkeypatch)
    out = capsys.readouterr().out
    assert "Timeframe Alignment" in out
    assert "Weekly" in out
    assert "Daily" in out
    assert "4H" in out


def test_scores_section(monkeypatch, capsys):
    _run(monkeypatch)
    out = capsys.readouterr().out
    assert "Scores" in out
    assert "Weekly" in out
    assert "Total" in out


def test_analysis_section(monkeypatch, capsys):
    _run(monkeypatch)
    out = capsys.readouterr().out
    assert "Analysis" in out
    assert "Global bias" in out
    assert "Confidence" in out
    assert "Validity" in out


def test_indicator_values_section(monkeypatch, capsys):
    _run(monkeypatch)
    out = capsys.readouterr().out
    assert "Indicator Values" in out
    assert "MACD line" in out
    assert "BB upper" in out
    assert "Stoch K / D" in out


def test_trade_plan_section(monkeypatch, capsys):
    _run(monkeypatch)
    out = capsys.readouterr().out
    assert "Trade Plan" in out


def test_bullish_trend_with_uptrend_data(monkeypatch, capsys):
    # The mock data is a linear uptrend — all indicators should lean bullish.
    _run(monkeypatch)
    out = capsys.readouterr().out
    assert "bullish" in out


def test_bar_counts_shown(monkeypatch, capsys):
    _run(monkeypatch)
    out = capsys.readouterr().out
    # 60 weekly bars
    assert "60W" in out


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_no_search_results_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["swing_trade.py", "XYZNOTFOUND"])
    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.search_for_stock.return_value = []
        with pytest.raises(SystemExit) as exc:
            load_script("swing_trade").main()
    assert exc.value.code == 1


def test_insufficient_chart_data_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["swing_trade.py", "APPLE"])
    with patch("avanza.Avanza") as MockAvanza:
        inst = MockAvanza.return_value
        inst.search_for_stock.return_value = MOCK_SEARCH_HITS
        inst.get_chart_data.side_effect = [[], [], []]
        with pytest.raises(SystemExit) as exc:
            load_script("swing_trade").main()
    assert exc.value.code == 1


def test_missing_argv_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["swing_trade.py"])
    with patch("avanza.Avanza"):
        with pytest.raises(SystemExit) as exc:
            load_script("swing_trade").main()
    assert exc.value.code == 1


def test_no_4h_data_still_runs(monkeypatch, capsys):
    # Script should complete even when hourly data returns empty.
    _run(monkeypatch, hourly={"ohlc": [], "from": "", "to": "", "previousClosingPrice": 0})
    out = capsys.readouterr().out
    assert "Swing Trade Analysis" in out
    assert "0 4H bars" in out


# ---------------------------------------------------------------------------
# Indicator unit tests
# ---------------------------------------------------------------------------

def test_compute_macd_returns_none_for_short_series():
    st = load_script("swing_trade")
    assert st.compute_macd([1.0] * 10) == (None, None, None)


def test_compute_macd_bullish_on_uptrend():
    st = load_script("swing_trade")
    prices = [100.0 + i * 0.3 for i in range(50)]
    macd, sig, hist = st.compute_macd(prices)
    assert macd is not None
    assert macd > sig  # uptrend → MACD above signal


def test_compute_bollinger_above_midline_on_uptrend():
    st = load_script("swing_trade")
    prices = [100.0 + i * 0.5 for i in range(30)]
    upper, mid, lower, bw = st.compute_bollinger(prices)
    assert upper > mid > lower
    assert prices[-1] > mid  # price above midline in uptrend


def test_compute_stochastic_range():
    st = load_script("swing_trade")
    closes = [100.0 + i * 0.1 for i in range(20)]
    highs  = [c + 0.5 for c in closes]
    lows   = [c - 0.5 for c in closes]
    k, d = st.compute_stochastic(highs, lows, closes)
    assert k is not None and 0 <= k <= 100
    assert d is not None and 0 <= d <= 100


def test_analyze_volume_strong():
    st = load_script("swing_trade")
    vols = [1_000_000] * 20 + [2_000_000]  # spike on last bar
    status, ratio = st.analyze_volume(vols)
    assert status == "strong"
    assert ratio >= 1.2


def test_analyze_volume_weak():
    st = load_script("swing_trade")
    vols = [1_000_000] * 20 + [500_000]  # drop on last bar
    status, ratio = st.analyze_volume(vols)
    assert status == "weak"
    assert ratio <= 0.8


def test_aggregate_to_4h():
    st = load_script("swing_trade")
    hourly = [
        {"timestamp": i * 3_600_000, "open": 100.0, "close": 101.0 + i,
         "high": 102.0, "low": 99.0, "totalVolumeTraded": 500_000}
        for i in range(8)
    ]
    bars = st.aggregate_to_4h(hourly)
    assert len(bars) == 2
    assert bars[0]["open"] == 100.0
    assert bars[0]["close"] == hourly[3]["close"]
    assert bars[0]["totalVolumeTraded"] == 2_000_000


def test_extract_orderbook_id():
    st = load_script("swing_trade")
    assert st.extract_orderbook_id({"path": "/aktier/usa/apple-inc/5447"}) == "5447"
    assert st.extract_orderbook_id({"path": "/aktier/om-aktien.html/12345/microsoft"}) == "12345"
    assert st.extract_orderbook_id({"path": "/no-numeric-here"}) is None


def test_fusion_no_trade_on_weak_volume():
    st = load_script("swing_trade")
    strategy, bias = st.apply_fusion("bullish", "bullish", "bullish", "weak", "weak", "weak")
    assert strategy == "no_trade"
    assert bias == "neutral"


def test_fusion_trend_following():
    st = load_script("swing_trade")
    strategy, bias = st.apply_fusion("bullish", "bullish", "bullish", "strong", "strong", "neutral")
    assert strategy == "trend_following"
    assert bias == "bullish"


def test_fusion_pullback_entry():
    st = load_script("swing_trade")
    strategy, bias = st.apply_fusion("bullish", "bearish", "bullish", "strong", "neutral", "strong")
    assert strategy == "pullback_entry"
    assert bias == "bullish"

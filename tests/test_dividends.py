import sys
from unittest.mock import patch

import pytest

from tests.conftest import load_script

MOCK_DIVIDEND_TXNS = {
    "transactions": [
        {
            "isin": "US0378331005",
            "instrumentName": "APPLE INC",
            "tradeDate": "2026-02-15",
            "type": "DIVIDEND",
            "volume": None,
            "amount": {"value": 350.0},
        },
        {
            "isin": "US0378331005",
            "instrumentName": "APPLE INC",
            "tradeDate": "2026-04-15",
            "type": "DIVIDEND",
            "volume": None,
            "amount": {"value": 360.0},
        },
        {
            "isin": "US5949181045",
            "instrumentName": "MICROSOFT CORP",
            "tradeDate": "2026-03-10",
            "type": "DIVIDEND",
            "volume": None,
            "amount": {"value": 800.0},
        },
    ]
}


def test_shows_dividend_table(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["dividends.py", "2026"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_transactions_details.return_value = MOCK_DIVIDEND_TXNS
        load_script("dividends").main()

    out = capsys.readouterr().out
    assert "Dividend Income — 2026" in out
    assert "APPLE INC" in out
    assert "MICROSOFT CORP" in out
    assert "710.00" in out    # 350 + 360 for Apple
    assert "800.00" in out    # Microsoft
    assert "TOTAL" in out


def test_sorted_by_total_descending(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["dividends.py", "2026"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_transactions_details.return_value = MOCK_DIVIDEND_TXNS
        load_script("dividends").main()

    out = capsys.readouterr().out
    # MICROSOFT (800) should appear before APPLE (710)
    msft_pos = out.find("MICROSOFT CORP")
    apple_pos = out.find("APPLE INC")
    assert msft_pos < apple_pos


def test_shows_monthly_breakdown(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["dividends.py", "2026"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_transactions_details.return_value = MOCK_DIVIDEND_TXNS
        load_script("dividends").main()

    out = capsys.readouterr().out
    assert "By Month" in out
    assert "2026-02" in out
    assert "2026-03" in out
    assert "2026-04" in out


def test_no_dividends(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["dividends.py", "2020"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_transactions_details.return_value = {"transactions": []}
        load_script("dividends").main()

    out = capsys.readouterr().out
    assert "No dividend payments found" in out

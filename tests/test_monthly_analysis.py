import sys
from unittest.mock import patch

import pytest

from tests.conftest import MOCK_POSITIONS, load_script

MOCK_BUY_TXNS = {
    "transactions": [
        {
            "isin": "US0378331005",
            "instrumentName": "APPLE INC",
            "tradeDate": "2026-03-15",
            "type": "BUY",
            "volume": {"value": 10.0},
            "amount": {"value": 20_050.0},
            "commission": {"value": 50.0},
            "orderbook": {"id": "5447"},
        },
    ]
}


def test_shows_monthly_analysis(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["monthly_analysis.py", "2026-03"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_transactions_details.return_value = MOCK_BUY_TXNS
        MockAvanza.return_value.get_accounts_positions.return_value = MOCK_POSITIONS
        load_script("monthly_analysis").main()

    out = capsys.readouterr().out
    assert "Monthly Investment Analysis" in out
    assert "2026-03" in out
    assert "APPLE INC" in out
    assert "20,050.00" in out
    assert "TOTAL" in out


def test_no_buys_in_month(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["monthly_analysis.py", "2025-01"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_transactions_details.return_value = {"transactions": []}
        load_script("monthly_analysis").main()

    out = capsys.readouterr().out
    assert "No BUY transactions" in out


def test_gain_shown_when_position_priced(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["monthly_analysis.py", "2026-03"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_transactions_details.return_value = MOCK_BUY_TXNS
        MockAvanza.return_value.get_accounts_positions.return_value = MOCK_POSITIONS
        load_script("monthly_analysis").main()

    out = capsys.readouterr().out
    # APPLE: 10 shares @ current price 25000/10 = 2500 SEK each
    # deployed: 20050 SEK, now worth: 10 * 2500 = 25000 SEK, gain: 4950 SEK
    assert "25,000.00" in out
    assert "live" in out

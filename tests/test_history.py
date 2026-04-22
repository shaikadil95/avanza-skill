import sys
from unittest.mock import patch

import pytest

from tests.conftest import load_script

MOCK_TRANSACTIONS = {
    "transactions": [
        {
            "tradeDate": "2026-04-10",
            "instrumentName": "APPLE INC",
            "description": "BUY APPLE INC",
            "type": "BUY",
            "volume": {"value": 5.0},
            "priceInTransactionCurrency": {"value": 2_000.0},
            "amount": {"value": 10_025.0},
            "commission": {"value": 25.0},
        },
        {
            "tradeDate": "2026-04-05",
            "instrumentName": "MICROSOFT CORP",
            "description": "SELL MICROSOFT",
            "type": "SELL",
            "volume": {"value": -3.0},
            "priceInTransactionCurrency": {"value": 3_100.0},
            "amount": {"value": -9_300.0},
            "commission": {"value": 15.0},
        },
    ]
}


def test_shows_transaction_table(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["history.py"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_transactions_details.return_value = MOCK_TRANSACTIONS
        load_script("history").main()

    out = capsys.readouterr().out
    assert "Transactions" in out
    assert "APPLE INC" in out
    assert "MICROSOFT CORP" in out
    assert "BUY" in out
    assert "SELL" in out
    assert "2 transaction" in out


def test_custom_date_range(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["history.py", "2026-03-01", "2026-03-31"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_transactions_details.return_value = MOCK_TRANSACTIONS
        load_script("history").main()

    out = capsys.readouterr().out
    assert "2026-03-01 → 2026-03-31" in out


def test_no_transactions(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["history.py"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_transactions_details.return_value = {"transactions": []}
        load_script("history").main()

    out = capsys.readouterr().out
    assert "No transactions found" in out


def test_invalid_date_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["history.py", "not-a-date"])

    with pytest.raises(SystemExit) as exc:
        load_script("history").main()

    assert exc.value.code == 1

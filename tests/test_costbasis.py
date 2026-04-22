import sys
from unittest.mock import patch

import pytest

from tests.conftest import MOCK_BUY_TRANSACTIONS, MOCK_POSITIONS, load_script


def test_shows_cost_basis_table(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["costbasis.py", "APPLE"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_accounts_positions.return_value = MOCK_POSITIONS
        MockAvanza.return_value.get_transactions_details.return_value = MOCK_BUY_TRANSACTIONS
        load_script("costbasis").main()

    out = capsys.readouterr().out
    assert "Cost Basis — APPLE INC" in out
    assert "US0378331005" in out
    assert "2026-01-15" in out
    assert "2026-03-10" in out
    assert "Avg cost basis" in out


def test_cumulative_avg_increases(monkeypatch, capsys):
    """Second lot at 2100 → cumulative avg should be between 1900 and 2100."""
    monkeypatch.setattr(sys, "argv", ["costbasis.py", "APPLE"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_accounts_positions.return_value = MOCK_POSITIONS
        MockAvanza.return_value.get_transactions_details.return_value = MOCK_BUY_TRANSACTIONS
        load_script("costbasis").main()

    out = capsys.readouterr().out
    # Total cost: 9525 + 10525 = 20050 over 10 shares → avg = 2005.00
    assert "2,005.00" in out


def test_isin_query(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["costbasis.py", "US0378331005"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_accounts_positions.return_value = MOCK_POSITIONS
        MockAvanza.return_value.get_transactions_details.return_value = MOCK_BUY_TRANSACTIONS
        load_script("costbasis").main()

    out = capsys.readouterr().out
    assert "Cost Basis — APPLE INC" in out


def test_stock_not_found_exits(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["costbasis.py", "NONEXISTENT"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_accounts_positions.return_value = MOCK_POSITIONS
        with pytest.raises(SystemExit) as exc:
            load_script("costbasis").main()

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "No current position found" in err


def test_missing_arg_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["costbasis.py"])

    with pytest.raises(SystemExit) as exc:
        load_script("costbasis").main()

    assert exc.value.code == 1


def test_shows_unrealised_gain(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["costbasis.py", "APPLE"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_accounts_positions.return_value = MOCK_POSITIONS
        MockAvanza.return_value.get_transactions_details.return_value = MOCK_BUY_TRANSACTIONS
        load_script("costbasis").main()

    out = capsys.readouterr().out
    assert "Current price" in out
    assert "Unrealised gain" in out
    assert "Return since 1st purchase" in out

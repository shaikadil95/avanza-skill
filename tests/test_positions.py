import sys
from unittest.mock import patch

import pytest

from tests.conftest import MOCK_POSITIONS, load_script


def test_shows_positions_table(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["positions.py"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_accounts_positions.return_value = MOCK_POSITIONS
        load_script("positions").main()

    out = capsys.readouterr().out
    assert "Holdings" in out
    assert "APPLE INC" in out
    assert "MICROSOFT CORP" in out
    assert "25,000.00" in out
    assert "TOTAL" in out


def test_gain_calculation(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["positions.py"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_accounts_positions.return_value = MOCK_POSITIONS
        load_script("positions").main()

    out = capsys.readouterr().out
    # APPLE: value 25000 - invested 20000 = gain 5000
    assert "5,000.00" in out
    # MICROSOFT: 15000 - 12000 = 3000
    assert "3,000.00" in out


def test_shows_cash_positions(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["positions.py"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_accounts_positions.return_value = MOCK_POSITIONS
        load_script("positions").main()

    out = capsys.readouterr().out
    assert "Cash" in out
    assert "ISK Account" in out
    assert "5,000.00" in out

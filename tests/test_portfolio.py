import sys
from unittest.mock import patch

import pytest

from tests.conftest import MOCK_OVERVIEW, load_script


def test_shows_account_table(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["portfolio.py"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_overview.return_value = MOCK_OVERVIEW
        load_script("portfolio").main()

    out = capsys.readouterr().out
    assert "Portfolio Overview" in out
    assert "Min ISK" in out
    assert "Min KF" in out
    assert "100,000.00" in out
    assert "15,000.00" in out
    assert "TOTAL" in out
    assert "150,000.00" in out  # sum of both accounts


def test_account_type_abbreviation(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["portfolio.py"])

    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_overview.return_value = MOCK_OVERVIEW
        load_script("portfolio").main()

    out = capsys.readouterr().out
    assert "ISK" in out
    assert "KF" in out


def test_credential_check_exits(monkeypatch):
    monkeypatch.delenv("AVANZA_USERNAME", raising=False)
    monkeypatch.setattr(sys, "argv", ["portfolio.py"])

    with pytest.raises(SystemExit) as exc:
        load_script("portfolio").main()

    assert exc.value.code == 1

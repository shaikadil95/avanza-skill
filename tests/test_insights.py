import sys
from unittest.mock import patch

import pytest

from tests.conftest import MOCK_INSIGHTS_REPORT, MOCK_OVERVIEW, load_script


def _run(monkeypatch, period_arg=None):
    argv = ["insights.py"] + ([period_arg] if period_arg else [])
    monkeypatch.setattr(sys, "argv", argv)
    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_overview.return_value = MOCK_OVERVIEW
        MockAvanza.return_value.get_insights_report.return_value = MOCK_INSIGHTS_REPORT
        load_script("insights").main()


def test_ytd_shows_overall_development(monkeypatch, capsys):
    _run(monkeypatch, "ytd")
    out = capsys.readouterr().out
    assert "Portfolio Insights" in out
    assert "Year-to-date" in out
    assert "Overall Development" in out
    assert "80,000.00" in out   # start
    assert "20,000.00" in out   # change


def test_shows_best_and_worst(monkeypatch, capsys):
    _run(monkeypatch, "ytd")
    out = capsys.readouterr().out
    assert "Best Performers" in out
    assert "APPLE INC" in out
    assert "Worst Performers" in out
    assert "BERKSHIRE HATHAWAY" in out


def test_shows_breakdown(monkeypatch, capsys):
    _run(monkeypatch, "ytd")
    out = capsys.readouterr().out
    assert "Breakdown" in out
    assert "18,000.00" in out   # price appreciation
    assert "2,000.00" in out    # dividends


def test_week_period(monkeypatch, capsys):
    _run(monkeypatch, "week")
    out = capsys.readouterr().out
    assert "Last 7 days" in out


def test_unknown_period_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["insights.py", "5y"])
    with pytest.raises(SystemExit) as exc:
        load_script("insights").main()
    assert exc.value.code == 1

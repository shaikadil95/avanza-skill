import sys
from unittest.mock import patch

import pytest

from tests.conftest import MOCK_INDEX_INFO, MOCK_INSIGHTS_REPORT, MOCK_OVERVIEW, load_script


def _run(monkeypatch, period=None, index_info=None):
    argv = ["compare.py"] + ([period] if period else [])
    monkeypatch.setattr(sys, "argv", argv)
    with patch("avanza.Avanza") as MockAvanza:
        MockAvanza.return_value.get_overview.return_value = MOCK_OVERVIEW
        MockAvanza.return_value.get_insights_report.return_value = MOCK_INSIGHTS_REPORT
        MockAvanza.return_value.get_index_info.return_value = index_info or MOCK_INDEX_INFO
        load_script("compare").main()


def test_ytd_shows_portfolio_and_benchmarks(monkeypatch, capsys):
    _run(monkeypatch, "ytd")
    out = capsys.readouterr().out
    assert "Portfolio vs Benchmarks" in out
    assert "Year-to-date" in out
    assert "Portfolio" in out
    assert "OMXS30" in out
    assert "OMXSPI" in out


def test_portfolio_return_displayed(monkeypatch, capsys):
    _run(monkeypatch, "ytd")
    out = capsys.readouterr().out
    # Portfolio return is 25.0% from mock
    assert "+25.00%" in out


def test_benchmark_return_and_alpha(monkeypatch, capsys):
    _run(monkeypatch, "ytd")
    out = capsys.readouterr().out
    # OMXS30 startOfYear = 8.5% → alpha = 25.0 - 8.5 = 16.5%
    assert "+8.50%" in out
    assert "+16.50%" in out


def test_week_period(monkeypatch, capsys):
    _run(monkeypatch, "week")
    out = capsys.readouterr().out
    assert "Last 7 days" in out
    # OMXS30 oneWeek = 1.2%
    assert "+1.20%" in out


def test_today_period(monkeypatch, capsys):
    _run(monkeypatch, "today")
    out = capsys.readouterr().out
    assert "Today" in out


def test_three_year_period(monkeypatch, capsys):
    _run(monkeypatch, "3y")
    out = capsys.readouterr().out
    assert "3-year rolling" in out
    # OMXS30 threeYears = 25.0%
    assert "+25.00%" in out


def test_unknown_period_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["compare.py", "5y"])
    with pytest.raises(SystemExit) as exc:
        with patch("avanza.Avanza"):
            load_script("compare").main()
    assert exc.value.code == 1


def test_includes_note_about_fx(monkeypatch, capsys):
    _run(monkeypatch, "ytd")
    out = capsys.readouterr().out
    assert "not FX-adjusted" in out

import importlib.util
import os
import sys

import pytest

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))


def load_script(name: str):
    """Load a script from scripts/ as a fresh module (avanza imports happen lazily inside main())."""
    path = os.path.join(SCRIPTS_DIR, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def credentials(monkeypatch):
    monkeypatch.setenv("AVANZA_USERNAME", "test_user")
    monkeypatch.setenv("AVANZA_PASSWORD", "test_pass")
    monkeypatch.setenv("AVANZA_TOTP_SECRET", "test_totp")


# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

MOCK_OVERVIEW = {
    "accounts": [
        {
            "id": "11111",
            "urlParameterId": "11111",
            "type": "INVESTERINGSSPARKONTO",
            "name": {"defaultName": "Min ISK", "userDefinedName": None},
            "balance": {"value": 5_000.0, "unit": "SEK"},
            "totalValue": {"value": 100_000.0, "unit": "SEK"},
            "profit": {"absolute": {"value": 15_000.0}, "relative": {"value": 17.6}},
        },
        {
            "id": "22222",
            "urlParameterId": "22222",
            "type": "KAPITALFORSAKRING",
            "name": {"defaultName": "Min KF", "userDefinedName": None},
            "balance": {"value": 2_000.0, "unit": "SEK"},
            "totalValue": {"value": 50_000.0, "unit": "SEK"},
            "profit": {"absolute": {"value": 5_000.0}, "relative": {"value": 11.1}},
        },
    ]
}

MOCK_POSITIONS = {
    "withOrderbook": [
        {
            "instrument": {
                "name": "APPLE INC",
                "isin": "US0378331005",
                "type": "STOCK",
                "currency": "USD",
                "orderbook": {"id": "5447", "flagCode": "US"},
            },
            "volume": {"value": 10.0},
            "value": {"value": 25_000.0},
            "acquiredValue": {"value": 20_000.0},
            "averageAcquiredPrice": {"value": 2_000.0},
            "lastTradingDayPerformance": {
                "relative": {"value": 1.5},
                "absolute": {"value": 375.0},
            },
        },
        {
            "instrument": {
                "name": "MICROSOFT CORP",
                "isin": "US5949181045",
                "type": "STOCK",
                "currency": "USD",
                "orderbook": {"id": "2455", "flagCode": "US"},
            },
            "volume": {"value": 5.0},
            "value": {"value": 15_000.0},
            "acquiredValue": {"value": 12_000.0},
            "averageAcquiredPrice": {"value": 2_400.0},
            "lastTradingDayPerformance": {
                "relative": {"value": -0.5},
                "absolute": {"value": -60.0},
            },
        },
    ],
    "cashPositions": [
        {
            "account": {"name": "ISK Account", "id": "11111"},
            "totalBalance": {"value": 5_000.0, "unit": "SEK"},
        }
    ],
}

MOCK_BUY_TRANSACTIONS = {
    "transactions": [
        {
            "isin": "US0378331005",
            "instrumentName": "APPLE INC",
            "tradeDate": "2026-01-15",
            "type": "BUY",
            "volume": {"value": 5.0},
            "priceInTransactionCurrency": {"value": 1_900.0},
            "priceInTradedCurrency": {"value": 175.0},
            "amount": {"value": 9_525.0},
            "commission": {"value": 25.0},
            "orderbook": {"id": "5447"},
        },
        {
            "isin": "US0378331005",
            "instrumentName": "APPLE INC",
            "tradeDate": "2026-03-10",
            "type": "BUY",
            "volume": {"value": 5.0},
            "priceInTransactionCurrency": {"value": 2_100.0},
            "priceInTradedCurrency": {"value": 193.0},
            "amount": {"value": 10_525.0},
            "commission": {"value": 25.0},
            "orderbook": {"id": "5447"},
        },
    ]
}

MOCK_INSIGHTS_REPORT = {
    "totalDevelopment": {
        "startingValue": 80_000.0,
        "endValue": 100_000.0,
        "totalChange": 20_000.0,
        "totalChangePercent": 25.0,
    },
    "from": "2026-01-01",
    "to": "2026-04-23",
    "developmentResponse": {
        "totalOutcome": {
            "development": 18_000.0,
            "dividends": 2_000.0,
            "total": 20_000.0,
        },
        "bestAndWorst": {
            "bestPositions": [
                {
                    "name": "APPLE INC",
                    "development": 5_000.0,
                    "totalDevelopmentInPercent": 25.0,
                    "endValue": 25_000.0,
                }
            ],
            "worstPositions": [
                {
                    "name": "BERKSHIRE HATHAWAY",
                    "development": -500.0,
                    "totalDevelopmentInPercent": -2.5,
                    "endValue": 19_500.0,
                }
            ],
        },
    },
}

MOCK_INDEX_INFO = {
    "name": "OMXS30",
    "historicalClosingPrices": {
        "oneDay": -0.5,
        "oneWeek": 1.2,
        "startOfYear": 8.5,
        "threeYears": 25.0,
    },
}

MOCK_STOCK_INFO = {
    "name": "APPLE INC",
    "sectors": [{"sectorName": "Technology", "sectorId": "1"}],
    "listing": {"countryCode": "US", "currency": "USD"},
}

# Upcoming Features

This skill is and will remain **read-only and analysis-only**. No order placement, account modification, or any write operations will ever be added.

Features planned for future iterations, roughly in priority order.

---

## ~~Iteration 3 — Per-stock history & cost basis~~ ✓ Implemented

### Return since first purchase
Show each position's return calculated from the actual first purchase date.

**Implemented** as `costbasis.py` — shows first buy date, price then, current price, and total return % since first purchase alongside the cumulative avg cost basis table.

### Average cost basis drill-down
For a specific stock, show every purchase event (date, shares, price, total cost) building up to the current average cost basis.

**Implemented** as `costbasis.py`:

```
/avanza costbasis APPLE
/avanza costbasis US0378331005
```

---

## ~~Iteration 4 — Portfolio composition & allocation~~ ✓ Implemented

### Sector / asset allocation
Break down the portfolio by sector, geography, or instrument type.

**Implemented** as `allocation.py`:

```
/avanza allocation
```

Output: asset type breakdown (STOCK/FUND/ETF/CASH), sector breakdown per stock via `get_stock_info()`, and currency exposure.

### Concentration risk
Highlight positions that exceed 10% of portfolio and flag non-SEK currency exposure.

**Implemented** in `allocation.py` — positions ≥ 10% are listed with a `[HIGH]` marker for those ≥ 20%.

---

## ~~Iteration 5 — Performance benchmarking~~ ✓ Implemented

### Compare portfolio to index
Compare portfolio return to OMXS30 and OMXSPI for a chosen period.

**Implemented** as `compare.py`:

```
/avanza compare ytd
/avanza compare week
/avanza compare 3y
```

Uses `get_insights_report()` for portfolio return and `get_index_info()` `historicalClosingPrices` for index returns. Shows alpha (portfolio − benchmark) for each index.

### Sharpe / volatility metrics
Compute annualised return, volatility, and a rough Sharpe ratio using daily close prices.

Not yet implemented — planned for a future iteration using `get_chart_data()`.

---

## Iteration 6 — Cash flow analysis

### Net cash flow over time
Show deposits minus withdrawals per month/year, making it easy to see how much new money was added vs organic growth.

```
/avanza cashflow 2025
```

### Reinvestment rate
What percentage of dividends received were reinvested (appeared as a BUY within N days)?

---

## Iteration 7 — Watchlist analysis

### Watchlist viewer
Show all instruments on your Avanza watchlist with current price, day change, and 52-week range — read-only.

```
/avanza watchlist
```

---

## Iteration 8 — Tax & reporting

### Realised gains report
List all closed positions for a tax year with: purchase date, sale date, profit/loss — formatted for Swedish K4 declaration.

```
/avanza tax 2025
```

### Dividend withholding tax summary
Show foreign dividends with the withheld tax rate per country, useful for tax reclaim filings.

---

## Ideas backlog (unscheduled)

- **Dollar-cost averaging tracker** — for positions bought in recurring instalments, show whether the DCA strategy is ahead of a lump-sum equivalent
- **ISK tax calculation** — estimate the annual ISK flat-rate tax (schablonskatt) based on current portfolio value
- **Order book viewer** — show bid/ask depth for a specific instrument
- **Multi-currency normalisation** — convert all positions to a single currency for a clean total when holding USD/EUR instruments
- **Sharpe / volatility metrics** — annualised return, volatility, Sharpe ratio via `get_chart_data()` daily closes

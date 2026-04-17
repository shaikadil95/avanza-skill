# Upcoming Features

This skill is and will remain **read-only and analysis-only**. No order placement, account modification, or any write operations will ever be added.

Features planned for future iterations, roughly in priority order.

---

## Iteration 3 — Per-stock history & cost basis

### Return since first purchase
Show each position's return calculated from the actual first purchase date, not just the running average buy price.

- Fetch BUY transactions per stock to find the earliest purchase date
- Use `get_chart_data()` to pull price history from that date to today
- Display: first buy date, price then, price now, total return %

### Average cost basis drill-down
For a specific stock, show every purchase event (date, shares, price, total cost) building up to the current average cost basis.

```
/avanza costbasis VOLV-B
```

---

## Iteration 4 — Portfolio composition & allocation

### Sector / asset allocation
Break down the portfolio by sector, geography, or instrument type (stocks, funds, ETFs) using data from `get_stock_info()`.

```
/avanza allocation
```

Output: pie-style text breakdown showing % of portfolio per sector and asset class.

### Concentration risk
Highlight positions that exceed a threshold (e.g. > 10% of portfolio) and flag currency exposure for non-SEK holdings.

---

## Iteration 5 — Performance benchmarking

### Compare portfolio to index
Fetch chart data for a benchmark (e.g. OMXS30, S&P 500) and overlay it with portfolio performance for the same period.

```
/avanza compare ytd
/avanza compare 2025
```

### Sharpe / volatility metrics
Compute annualised return, volatility, and a rough Sharpe ratio using daily close prices over a chosen period.

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

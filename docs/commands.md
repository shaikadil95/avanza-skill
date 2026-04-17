# Command Reference

All commands are invoked via `/avanza [subcommand] [args]` inside Claude Code.  
Scripts can also be run directly: `uv run ~/.claude/skills/avanza/scripts/<name>.py`

---

## `portfolio` — Account overview

```
/avanza
/avanza portfolio
```

Shows a summary row per account:

| Field | Description |
|---|---|
| Account | User-defined or default account name |
| Balance | Available cash balance (SEK) |
| Total Value | Balance + market value of all holdings |
| Profit | Absolute gain since account was opened |
| Return | Relative gain % |

**Totals row** at the bottom aggregates across all accounts.

---

## `positions` — Holdings with gain/loss

```
/avanza positions
```

One row per held instrument:

| Field | Description |
|---|---|
| Stock | Instrument name |
| Shares | Number of shares held |
| Invested | Total amount paid to acquire current position |
| Value | Current market value |
| Gain (SEK) | Value − Invested |
| Gain % | (Gain / Invested) × 100 |
| Day % | Change since previous close |

Also prints a **Cash Positions** section showing uninvested cash per account.

---

## `transactions` — Transaction history

```
/avanza transactions
/avanza transactions 2026-03-01 2026-03-31
```

**Arguments:**
- `from-date` — start date in `YYYY-MM-DD` format (default: first day of current month)
- `to-date` — end date in `YYYY-MM-DD` format (default: today)

Covers all transaction types: BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAW.

| Field | Description |
|---|---|
| Date | Trade date |
| Instrument | Stock or fund name |
| Type | BUY / SELL / DIVIDEND / DEPOSIT / WITHDRAW |
| Shares | Volume traded |
| Price | Price per share in transaction currency |
| Amount | Total transaction value (SEK) |
| Commission | Brokerage fee |

Footer shows total amount and total commission for the period.

---

## `monthly` — Monthly deployment analysis

```
/avanza monthly
/avanza monthly 2026-03
```

**Argument:** `YYYY-MM` month to analyse (default: previous calendar month).

Answers: *"I invested X SEK in March — what are those specific shares worth today?"*

| Field | Description |
|---|---|
| Stock | Instrument name |
| Shares | Number of shares bought that month |
| Deployed | Total cost of those purchases |
| Now Worth | Current market value of those same shares |
| Gain (SEK) | Now Worth − Deployed |
| Gain % | Return since purchase |
| Price? | `live` = priced from current positions; `n/a` = position fully closed |

For stocks that have since been sold, the script fetches current market price via the order book so you still see the return on that capital.

---

## `insights` — Performance report

```
/avanza insights
/avanza insights ytd
/avanza insights week
/avanza insights today
/avanza insights 3y
```

**Argument:** time period (default: `ytd`)

| Period | Description |
|---|---|
| `today` | Since market open today |
| `week` | Last 7 days |
| `ytd` | Since 1 January of current year |
| `3y` | 3-year rolling window |

Output sections:

1. **Overall Development** — start value, end value, total gain (SEK + %)
2. **Breakdown** — price appreciation vs dividend income vs combined total
3. **Best Performers** — top 5 positions by return %
4. **Worst Performers** — bottom 5 positions by return %

---

## `dividends` — Dividend tracker

```
/avanza dividends
/avanza dividends 2025
```

**Argument:** `YYYY` year (default: current year).

| Field | Description |
|---|---|
| Stock | Instrument name |
| Payments | Number of dividend events in the year |
| Total (SEK) | Sum of all payments from this stock |
| Latest date | Date of most recent payment |

Footer shows total payments count and grand total income.  
A **By Month** breakdown at the end shows when dividends were received throughout the year.

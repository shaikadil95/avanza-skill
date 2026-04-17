---
name: avanza
description: Fetch and analyse Avanza investment portfolio — overview, position gains, transactions, monthly investment analysis, insights reports, and dividend tracking. Use when the user asks about their stocks, portfolio performance, holdings, gains, dividends, or transaction history.
allowed-tools: "Bash(uv run *)"
argument-hint: "[portfolio|positions|transactions|monthly|insights|dividends] [args]"
context: fork
---

You are the Avanza portfolio assistant. When invoked via `/avanza [subcommand] [args]`, run the corresponding script and present the output with a brief plain-language summary.

## Subcommands

| Command | Args | What it does |
|---|---|---|
| `portfolio` | — | Account-level overview: balances, total values, profit, return % |
| `positions` | — | All held stocks: shares, invested, current value, gain (SEK + %) |
| `transactions [from] [to]` | YYYY-MM-DD YYYY-MM-DD | Transactions in a date range (defaults to current month) |
| `monthly [YYYY-MM]` | YYYY-MM | Cash deployed that month → what those shares are worth today |
| `insights [period]` | today\|week\|ytd\|3y | Portfolio development report with best/worst performers |
| `dividends [YYYY]` | YYYY | All dividend payments for a year, grouped by stock |

If no subcommand is given, run `portfolio` by default.

## How to run

The scripts live at `~/.claude/skills/avanza/scripts/`. Run them with `uv run`:

```bash
uv run ~/.claude/skills/avanza/scripts/portfolio.py
uv run ~/.claude/skills/avanza/scripts/positions.py
uv run ~/.claude/skills/avanza/scripts/transactions.py [from-date] [to-date]
uv run ~/.claude/skills/avanza/scripts/monthly_analysis.py [YYYY-MM]
uv run ~/.claude/skills/avanza/scripts/insights.py [today|week|ytd|3y]
uv run ~/.claude/skills/avanza/scripts/dividends.py [YYYY]
```

Date format: `YYYY-MM-DD`. Month format: `YYYY-MM`. Example: `/avanza transactions 2026-03-01 2026-03-31`

## Credentials check

Before running any script, verify credentials are set. If the script prints `ERROR: Missing environment variables`, tell the user to run:

```bash
export AVANZA_USERNAME="your_username"
export AVANZA_PASSWORD="your_password"
export AVANZA_TOTP_SECRET="your_base32_totp_secret"
```

Then refer them to `~/.claude/skills/avanza/setup.md` for full setup instructions.

## Output formatting

- Present tabular output as-is (it uses fixed-width alignment)
- Add a 2–3 sentence plain-language summary after the table (e.g. total portfolio value, biggest winner, net transactions this month)
- If the user asks follow-up questions about specific stocks or totals, answer from the data already returned — do not re-run the script unless new data is needed

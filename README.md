# avanza-skill

A **read-only** [Claude Code](https://claude.ai/code) skill that connects to your [Avanza](https://www.avanza.se) investment account and lets you analyse your portfolio directly from the Claude CLI. It never places orders, modifies your account, or writes any data to Avanza.

> **Disclaimer:** This project is not affiliated with or endorsed by Avanza Bank AB. It is built on top of [`avanza-api`](https://github.com/qluxzz/avanza), a community library that reverse-engineers Avanza's **private, undocumented API**. Avanza can change or remove any endpoint at any time without notice, which may break this skill. The developer is **not responsible** for data inaccuracies, service interruptions, or any decisions made based on this tool's output. Use at your own risk. See [docs/disclaimer.md](docs/disclaimer.md) for full details.

---

## What you can do

| Command | Description |
|---|---|
| `/avanza` | Account balances, total value, profit, return % |
| `/avanza positions` | Every holding with invested amount, current value, and gain/loss |
| `/avanza history [from] [to]` | Past BUY / SELL / DIVIDEND events in a date range (read-only) |
| `/avanza monthly [YYYY-MM]` | Cash deployed in a month → what those shares are worth today |
| `/avanza insights [period]` | Development report with best/worst performers and dividend breakdown |
| `/avanza dividends [YYYY]` | All dividend payments for a year, grouped by stock and month |

---

## Quick start

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install the skill

```bash
git clone https://github.com/shaikadil95/avanza-skill ~/.claude/skills/avanza
```

Or if you already have something at that path:

```bash
git clone https://github.com/shaikadil95/avanza-skill ~/projects/avanza-skill
ln -s ~/projects/avanza-skill ~/.claude/skills/avanza
```

### 3. Set credentials

Add to your `~/.zshrc` or `~/.zprofile`:

```bash
export AVANZA_USERNAME="your_username"
export AVANZA_PASSWORD="your_password"
export AVANZA_TOTP_SECRET="your_base32_totp_secret"
```

Get your TOTP secret from: **Avanza → Settings → Security → "Annan app för tvåfaktorsinloggning"**

### 4. Reload and test

```bash
source ~/.zshrc
uv run ~/.claude/skills/avanza/scripts/portfolio.py
```

For full setup details see [docs/setup.md](docs/setup.md).

---

## Example output

### `/avanza monthly 2026-03`

```
Monthly Investment Analysis — 2026-03

Period: 2026-03-01 → 2026-03-31

Stock                      Shares       Deployed      Now Worth   Gain (SEK)     Gain %   Price?
------------------------  --------  --------------  --------------  ------------  ----------  --------
AMAZON.COM                       2        3,850.00        4,620.40        770.40       20.0%      live
APPLE INC                        4        9,200.00        9,660.00        460.00        5.0%      live
MICROSOFT CORP                   6       21,600.00       23,976.00      2,376.00       11.0%      live
NVIDIA CORPORATION               8       12,400.00       14,136.00      1,736.00       14.0%      live
SOME ETF                        10        8,000.00        7,600.00       -400.00       -5.0%      live
------------------------  --------  --------------  --------------  ------------  ----------  --------
TOTAL                                    55,050.00       59,992.40      4,942.40        9.0%
```

In March 2026, **55,050 SEK** was deployed across 5 positions — now worth **59,992 SEK**, a gain of **+4,942 SEK (+9.0%)** in roughly four weeks. Microsoft and NVIDIA were the top contributors; the ETF position is the only laggard at -5.0%.

---

## Usage examples

```
/avanza                              # portfolio overview
/avanza positions                    # all holdings with gain/loss
/avanza history                      # trade history this month
/avanza history 2026-03-01 2026-03-31
/avanza monthly                      # last month's deployed cash vs today
/avanza monthly 2026-02
/avanza insights                     # year-to-date report
/avanza insights week
/avanza dividends                    # dividends this year
/avanza dividends 2025
```

---

## Documentation

- [Setup guide](docs/setup.md) — credentials, TOTP, first run
- [Command reference](docs/commands.md) — all commands with full output descriptions
- [Upcoming features](docs/upcoming.md) — planned usecases for future iterations
- [Disclaimer](docs/disclaimer.md) — liability, API stability, and usage warnings

---

## Tech stack

- **Runtime:** Python 3 + [`uv`](https://github.com/astral-sh/uv) inline script dependencies
- **API wrapper:** [`avanza-api`](https://pypi.org/project/avanza-api/) (auto-installed by uv on first run)
- **Auth:** TOTP-based 2FA via environment variables — no credentials stored on disk
- **Skill host:** [Claude Code](https://claude.ai/code)

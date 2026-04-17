# Avanza Skill — Setup

## 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 2. Set credentials as environment variables

Add these lines to your `~/.zshrc` or `~/.zprofile`:

```bash
export AVANZA_USERNAME="your_avanza_username"
export AVANZA_PASSWORD="your_avanza_password"
export AVANZA_TOTP_SECRET="your_base32_totp_secret"
```

Then reload your shell:

```bash
source ~/.zshrc
```

### How to get your TOTP secret

1. Log in to Avanza
2. Go to **Settings → Security → Two-factor authentication**
3. Click **"Annan app för tvåfaktorsinloggning"** (Other authenticator app)
4. You will see a QR code and a **Base32 secret key** — copy that key
5. That key is your `AVANZA_TOTP_SECRET`

> **Note:** The `avanza-api` Python package is installed automatically by `uv` on first run — no manual `pip install` needed.

## 3. Test the setup

```bash
uv run ~/.claude/skills/avanza/scripts/portfolio.py
```

## Usage

| Command | Description |
|---|---|
| `/avanza` | Portfolio overview (accounts, balances, profit) |
| `/avanza portfolio` | Same as above |
| `/avanza positions` | All holdings with gain/loss per stock |
| `/avanza transactions` | Transactions this month |
| `/avanza transactions 2026-03-01 2026-03-31` | Transactions in a specific range |

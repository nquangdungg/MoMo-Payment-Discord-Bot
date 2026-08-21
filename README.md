# MoMo Payment Bot

A Discord bot that lets users create real MoMo Wallet payment requests directly from a server, track their status automatically, and notify staff on success — all via slash commands.

🇻🇳 [Tiếng Việt](README.vi.md)

## Features

- `/thanhtoan <amount>` — creates a MoMo payment request (min. 2,000 VND), returns a pay link + QR code, and auto-polls MoMo until the transaction succeeds, fails, or expires (10 min).
- `/huygiaodich <transaction_id>` — cancels a pending transaction.
- Per-user rate limiting (60s cooldown, max 3 concurrent pending transactions).
- Automatic staff-channel notification when a payment is confirmed.
- Full MoMo v3 API error-code mapping with human-readable Vietnamese messages.
- Structured logging to `bot.log` (sensitive values are SHA-256 hashed before being logged).

## Project structure

```
momo-bot/
├── main.py                     # entry point: loads config, starts the bot
├── constants/
│   ├── config.py                # env vars & global constants
│   └── momo_errors.py           # MoMo API result-code lookup table
├── model/
│   └── transaction.py           # GiaoDich / RateLimitInfo dataclasses
├── utils/
│   ├── logger.py                 # logging setup
│   ├── security.py               # HMAC signature + hashing helpers
│   ├── discord_files.py          # base64 -> discord.File conversion
│   └── embeds.py                 # shared embed footer helper
├── services/
│   ├── momo_service.py           # calls to the MoMo /create and /query endpoints
│   └── transaction_service.py    # in-memory state, rate limiting, status polling loop
├── command/
│   └── payment_commands.py       # /thanhtoan and /huygiaodich slash commands (Cog)
├── requirements.txt
└── .env.example
```

## Requirements

- Python 3.10+
- A Discord bot application + token ([Discord Developer Portal](https://discord.com/developers/applications))
- A MoMo Business account with API access ([business.momo.vn](https://business.momo.vn))
- Two publicly reachable **HTTPS** endpoints for `ipnUrl` and `redirectUrl` (MoMo will call these back)

## Setup

1. Clone/copy the project, then install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy the env template and fill in your real values:

   ```bash
   cp .env.example .env
   ```

   | Variable | Description |
   |---|---|
   | `DISCORD_BOT_TOKEN` | Your Discord bot token |
   | `STAFF_CHANNEL_ID` | Channel ID where successful payments are announced |
   | `PARTNER_CODE` / `ACCESS_KEY` / `SECRET_KEY` | Credentials from your MoMo Business Portal |
   | `MOMO_ENDPOINT` | MoMo gateway base URL (defaults to production) |
   | `ipnUrl` / `redirectUrl` | Your HTTPS callback URLs registered with MoMo |

3. Invite the bot to your server with the `applications.commands` and `bot` scopes (message content intent enabled).

4. Run it:

   ```bash
   python main.py
   ```

   Slash commands are synced automatically on startup (`on_ready`).

## Notes / caveats

- This bot talks to MoMo's **production** endpoint by default — every transaction created is a real payment request. Point `MOMO_ENDPOINT` at MoMo's sandbox if you want to test without moving real money.
- Transaction state (`giao_dich_active`, rate-limit tracking) is kept **in memory only** — it resets if the process restarts, and won't work correctly across multiple bot instances/shards.
- The bot fetches the QR code by scraping MoMo's hosted pay page (`BeautifulSoup`) rather than pulling it from the `/create` API response — this is inherently fragile against changes to MoMo's page markup.
- No IPN webhook receiver is included; payment confirmation relies purely on polling `/query` every 30 seconds.

## License

Internal project — no license specified.

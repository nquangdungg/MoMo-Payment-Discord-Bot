# MoMo Payment Bot

A Discord bot for creating and managing MoMo Wallet payment requests directly from Discord. Users can generate a payment request, receive a payment link and QR code, and have the bot automatically track the transaction until it succeeds, fails, or expires.

🇻🇳 [Tiếng Việt](README.vi.md)

## Features

* `/thanhtoan <amount>` — creates a MoMo payment request with a minimum amount of **2,000 VND**, then returns a payment link and QR code. The bot automatically checks the transaction status until it succeeds, fails, or expires after 10 minutes.
* `/huygiaodich <transaction_id>` — cancels a pending transaction.
* **Per-user rate limiting** — users must wait 60 seconds between requests and can have up to 3 pending transactions at the same time.
* **Payment notifications** — automatically notifies the staff channel when a payment is confirmed.
* **MoMo v3 error handling** — maps MoMo API result codes to readable Vietnamese error messages.
* **Structured logging** — logs are written to `bot.log`, with sensitive values hashed using SHA-256 before being logged.

## Project Structure

```text
momo-bot/
├── main.py                     # Application entry point
├── constants/
│   ├── config.py               # Environment variables and global constants
│   └── momo_errors.py          # MoMo API result-code mappings
├── model/
│   └── transaction.py          # GiaoDich and RateLimitInfo dataclasses
├── utils/
│   ├── logger.py               # Logging configuration
│   ├── security.py             # HMAC signing and hashing utilities
│   ├── discord_files.py        # Converts base64 data to discord.File
│   └── embeds.py               # Shared Discord embed helpers
├── services/
│   ├── momo_service.py         # MoMo /create and /query API calls
│   └── transaction_service.py  # Transaction state, rate limiting, and polling
├── command/
│   └── payment_commands.py     # /thanhtoan and /huygiaodich slash commands
├── requirements.txt
└── .env.example
```

## Requirements

* **Python 3.10+**
* A Discord bot application and bot token from the [Discord Developer Portal](https://discord.com/developers/applications)
* A **MoMo Business** account with API access from [MoMo Business](https://business.momo.vn)
* Two publicly accessible **HTTPS** endpoints for `ipnUrl` and `redirectUrl`

## Setup

### 1. Install dependencies

Clone or copy the project, then install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Then fill in the required values:

| Variable            | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| `DISCORD_BOT_TOKEN` | Your Discord bot token                                       |
| `STAFF_CHANNEL_ID`  | Discord channel ID used for successful payment notifications |
| `PARTNER_CODE`      | MoMo Business partner code                                   |
| `ACCESS_KEY`        | MoMo API access key                                          |
| `SECRET_KEY`        | MoMo API secret key                                          |
| `MOMO_ENDPOINT`     | MoMo API base URL. Defaults to the production endpoint       |
| `ipnUrl`            | Public HTTPS URL registered with MoMo for IPN callbacks      |
| `redirectUrl`       | Public HTTPS URL registered with MoMo for redirects          |

### 3. Invite the bot

Invite the bot to your Discord server with the required `bot` and `applications.commands` scopes.

The bot also requires the **Message Content Intent** to be enabled in the Discord Developer Portal.

### 4. Start the bot

```bash
python main.py
```

Slash commands are automatically synchronized when the bot becomes ready.

## Notes

### Production payments

The bot uses MoMo's **production endpoint by default**. Any payment request created through the production endpoint represents a real transaction.

For testing, configure `MOMO_ENDPOINT` to use MoMo's sandbox environment instead.

### In-memory transaction state

Transaction state and rate-limit information are stored **in memory only**.

This means:

* All active transactions are lost when the bot restarts.
* Rate-limit information is reset on restart.
* Running multiple bot instances or shards is not supported correctly with the current implementation.

### QR code generation

The bot retrieves the QR code by scraping MoMo's hosted payment page with `BeautifulSoup` instead of receiving the QR data directly from the `/create` API response.

Because this depends on MoMo's page structure, changes to the payment page markup may break QR code extraction.

### Payment confirmation

The bot does not include an IPN webhook receiver. Instead, it checks the transaction status through MoMo's `/query` endpoint every 30 seconds until the transaction reaches a final state or expires.

## License

This project is open source and released under the **GNU General Public License v3.0 (GPL-3.0)**.

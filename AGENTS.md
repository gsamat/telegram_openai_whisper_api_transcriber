We r implementing telegram-bot using python-telegram-bot framework.

We have reference ../selfmailbot for project boilerplate

## Project Structure

```
bot-from-scratch/
├── src/
│   ├── __init__.py
│   ├── billing.py       # Billing system (SQLite)
│   ├── bot.py           # Bot handlers and main entry point
│   └── transcribe.py    # OpenAI Whisper integration
├── billing.db           # SQLite database (created at runtime)
├── .env.default         # Configuration template
└── pyproject.toml       # Dependencies
```

## Configuration

- `BOT_TOKEN` - Telegram bot token
- `DATABASE_PATH` - Path to SQLite database (default: `./billing.db`)
- `SECONDS_PER_STAR` - Conversion rate for Telegram Stars (default: 1800 = 30 minutes)

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/topup <amount>` | Purchase credits with Telegram Stars |
| `/balance` | Check current balance |

## Billing System

### Database Schema

```sql
CREATE TABLE billing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_hash TEXT NOT NULL,      -- SHA-256 hashed Telegram user ID
    amount REAL NOT NULL,          -- Positive for topups, negative for consumption (seconds)
    date TEXT NOT NULL,            -- ISO format timestamp (UTC)
    source TEXT NOT NULL           -- 'telegram_payment', 'transcribing', etc.
)
```

### Billing Functions (src/billing.py)

- `hash_user_id(user_id: int) -> str` - SHA-256 hash for privacy
- `init_billing_db()` - Create billing table if not exists
- `bill(user_hash, amount, source)` - Record billing entry
- `get_balance(user_hash) -> float` - Get user's current balance (SUM of amounts)

### Amount Convention

- **Positive**: Credits added (topups via Telegram Stars)
- **Negative**: Credits consumed (transcription seconds)
- Balance = `SUM(amount)` for a user

## Telegram Stars Payments

### Key Implementation Details

- Currency code: `XTR` (Telegram Stars)
- No `provider_token` needed for Stars (pass empty string or omit)
- `payload` parameter is **required** by Telegram API (1-128 bytes) - we use `"topup"`
- Price units: 1 star = 1 unit (unlike USD where 1$ = 100 cents)

### Payment Flow

1. User sends `/topup 5`
2. Bot calls `send_invoice()` with currency="XTR"
3. User pays through Telegram's payment interface
4. Bot receives `PreCheckoutQuery` → approves with `query.answer(ok=True)`
5. Payment completes → `SuccessfulPayment` received
6. Bot credits user: `bill(user_hash, +seconds, "telegram_payment")`

### Required Handlers

```python
from telegram import LabeledPrice
from telegram.ext import PreCheckoutQueryHandler, MessageHandler, filters

app.add_handler(CommandHandler("topup", topup))
app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
```

## Voice Transcription

- Uses OpenAI Whisper API via `src/transcribe.py`
- Bills user with negative amount: `bill(user_hash, -duration_seconds, "transcribing")`
- Supports both Voice and Audio messages
- In groups: bills the requester (not the voice sender)

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

### Billing Sources

| Source | Description |
|--------|-------------|
| `telegram_payment` | Credits from Telegram Stars payment |
| `transcribing` | Deduction for voice transcription (negative amount) |
| `welcome_bonus` | Auto-credit when balance is exactly 0 |
| `balance_adjustment` | Manual/administrative adjustments |

### Balance Check (Pre-Transcription)

Before transcribing, the bot checks user balance:

- **balance > 0**: Proceed with transcription
- **balance == 0**: Auto-credit 1800 seconds (source: `"welcome_bonus"`), then proceed
- **balance < 0**: Return `None`, show insufficient balance message with top-up keyboard

Implementation in `transcribe()` function (`src/bot.py`):

```python
async def transcribe(file, context, user_id) -> str | None:
    user_hash = hash_user_id(user_id)
    current_balance = await get_balance(user_hash)
    
    if current_balance == 0:
        await bill(user_hash, 1800, "welcome_bonus")
        current_balance = 1800
    
    if current_balance < 0:
        return None  # Insufficient balance
    
    # Proceed with transcription...
```

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
from telegram.ext import PreCheckoutQueryHandler, MessageHandler, CallbackQueryHandler, filters

app.add_handler(CommandHandler("topup", topup))
app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
app.add_handler(CallbackQueryHandler(topup_callback, pattern=r"^topup:\d+$"))
```

## Inline Keyboard Payments

For quick top-up buttons (e.g., when balance is insufficient):

### Implementation Pattern

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

def get_topup_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard with top-up buttons (2x2 grid)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1 ⭐", callback_data="topup:1"),
            InlineKeyboardButton("5 ⭐", callback_data="topup:5"),
        ],
        [
            InlineKeyboardButton("10 ⭐", callback_data="topup:10"),
            InlineKeyboardButton("20 ⭐", callback_data="topup:20"),
        ],
    ])

async def topup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle top-up button callback - send invoice for selected amount."""
    query = update.callback_query
    await query.answer()  # MUST call this first to acknowledge callback
    
    # Parse stars from callback_data (e.g., "topup:5")
    _, stars_str = query.data.split(":")
    stars = int(stars_str)
    
    # Calculate and send invoice
    total_seconds = stars * SECONDS_PER_STAR
    minutes = total_seconds // 60
    
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,  # Use query.message.chat_id
        title="Transcription Credits",
        description=f"Top up your balance with {minutes} minutes of voice transcription",
        payload="topup",
        currency="XTR",
        prices=[LabeledPrice("Transcription credits", stars)],
    )
```

### Usage in Messages

```python
await update.message.reply_text(
    "Insufficient balance. Please top up:",
    reply_markup=get_topup_keyboard(),
)
```

### Key Points

- **Must call `query.answer()`** before processing to acknowledge the callback
- Use `query.message.chat_id` (not `update.message.chat_id`) to get the chat ID
- Callback data format: `"topup:<amount>"` (e.g., `"topup:5"`)
- Register handler with pattern: `CallbackQueryHandler(callback_func, pattern=r"^topup:\d+$")`

## Voice Transcription

- Uses OpenAI Whisper API via `src/transcribe.py`
- Bills user with negative amount: `bill(user_hash, -duration_seconds, "transcribing")`
- Supports both Voice and Audio messages
- In groups: bills the requester (not the voice sender)

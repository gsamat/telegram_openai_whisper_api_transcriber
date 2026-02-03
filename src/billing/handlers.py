"""Billing handlers for Telegram bot - payments, balance, and top-ups."""

from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, PreCheckoutQueryHandler, filters

from config import SECONDS_PER_STAR, WELCOME_BONUS

from .db import bill, get_balance, hash_user_id

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


def get_topup_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard with top-up buttons (2x2 grid)."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("1 ⭐", callback_data="topup:1"),
                InlineKeyboardButton("5 ⭐", callback_data="topup:5"),
            ],
            [
                InlineKeyboardButton("10 ⭐", callback_data="topup:10"),
                InlineKeyboardButton("20 ⭐", callback_data="topup:20"),
            ],
        ]
    )


async def do_billing_stuff(user_id: int) -> float:
    """Check balance and apply welcome bonus if needed.

    Args:
        user_id: Telegram user ID

    Returns:
        Current balance.
    """
    user_hash = hash_user_id(user_id)
    current_balance = await get_balance(user_hash)

    if current_balance == 0:
        await bill(user_hash, WELCOME_BONUS, "welcome_bonus")
        return WELCOME_BONUS

    return current_balance


async def topup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /topup command - send invoice for Telegram Stars.

    Usage: /topup <amount>
    Example: /topup 5 (to purchase 5 stars worth of transcription credits)
    """
    if update.message is None:
        return

    # Parse amount from command args
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(f"Usage: /topup <amount>\nExample: /topup 5\n\n1 звезда дает {SECONDS_PER_STAR // 60} минут")
        return

    try:
        stars = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid positive integer amount.")
        return

    if stars <= 0:
        await update.message.reply_text("Amount must be a positive number.")
        return

    # Calculate transcription time
    total_seconds = stars * SECONDS_PER_STAR
    minutes = total_seconds // 60

    # Send invoice
    await context.bot.send_invoice(
        chat_id=update.message.chat_id,
        title="Transcription Credits",
        description=f"{minutes} minutes of voice transcription",
        payload="topup",
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice("Transcription credits", stars)],
    )


async def topup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle top-up button callback - send invoice for selected amount."""
    query = update.callback_query
    if query is None or query.data is None or query.message is None:
        return

    # Ensure message is accessible (not inaccessible/deleted)
    if not isinstance(query.message, Message):
        return

    await query.answer()

    # Parse stars from callback_data (e.g., "topup:5")
    _, stars_str = query.data.split(":")
    stars = int(stars_str)

    # Calculate transcription time
    total_seconds = stars * SECONDS_PER_STAR
    minutes = total_seconds // 60

    # Send invoice
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title="Transcription Credits",
        description=f"{minutes} minutes of voice transcription",
        payload="topup",
        currency="XTR",
        prices=[LabeledPrice("Transcription credits", stars)],
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /balance command - show user's current balance."""
    if update.message is None or update.message.from_user is None:
        return

    user_hash = hash_user_id(update.message.from_user.id)
    current_balance = await get_balance(user_hash)

    minutes = int(current_balance // 60)
    seconds = int(current_balance % 60)

    await update.message.reply_text(f"Ваш баланс {minutes} мин {seconds} сек")


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pre-checkout query - verify payment before processing."""
    query = update.pre_checkout_query
    if query is None:
        return

    # Verify payload matches our invoice
    if query.invoice_payload != "topup":
        await query.answer(ok=False, error_message="Invalid payment request.")
        return

    # Approve the payment
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle successful payment - credit user's balance."""
    if update.message is None or update.message.successful_payment is None or update.message.from_user is None:
        return

    payment = update.message.successful_payment
    user_id = update.message.from_user.id

    # Get stars from payment (already in star units for XTR currency)
    stars = payment.total_amount

    # Convert to seconds and credit the user
    credited_seconds = stars * SECONDS_PER_STAR
    user_hash = hash_user_id(user_id)
    await bill(user_hash, credited_seconds, "telegram_payment")

    # Confirm to user
    minutes = credited_seconds // 60
    await update.message.reply_text(f"Добавили {minutes} минут! Спасибо!")


def register_handlers(app: Application) -> None:
    """Register all billing-related handlers with the application.

    Args:
        app: Telegram Application instance
    """
    # Command handlers
    app.add_handler(CommandHandler("topup", topup))
    app.add_handler(CommandHandler("balance", balance))

    # Payment handlers
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(CallbackQueryHandler(topup_callback, pattern=r"^topup:\d+$"))

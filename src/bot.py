import contextlib
import os
from datetime import timedelta
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, PreCheckoutQueryHandler, filters

from billing import bill, get_balance, hash_user_id, init_billing_db
from transcribe import transcribe_voice

if TYPE_CHECKING:
    from telegram import Audio, Update, Voice

load_dotenv()

MAX_MESSAGE_LENGTH = 4096
SECONDS_PER_STAR = 60 * 30  # 1 star = 30 minutes of transcription


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


async def transcribe(
    file: Voice | Audio,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> str | None:
    """Transcribe voice message and bill the user.

    Args:
        file: Voice or Audio object from Telegram
        context: Bot context for downloading files
        user_id: Telegram user ID to bill

    Returns:
        Transcribed text, or None if balance is insufficient

    Raises:
        Exception: If transcription fails
    """
    # Check user balance
    user_hash = hash_user_id(user_id)
    current_balance = await get_balance(user_hash)

    # Auto-credit when balance is exactly 0
    if current_balance == 0:
        await bill(user_hash, 1800, "welcome_bonus")
        current_balance = 1800

    # Insufficient balance - return None
    if current_balance < 0:
        return None

    # Transcribe using OpenAI Whisper
    transcript = await transcribe_voice(file, context)

    # Bill user for transcription
    # file.duration can be int (seconds) or timedelta in python-telegram-bot
    duration = file.duration
    duration_float = duration.total_seconds() if isinstance(duration, timedelta) else float(duration)
    await bill(user_hash, -duration_float, "transcribing")

    return transcript


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    if update.message is None:
        return
    message = (
        "Привет! Я распознаю голосовые сообщения. Вы кидаете мне голосовое, я в ответ возвращаю его текстовую версию. \n \n"
        "Есть ограничение на максимальную длину голосового — около 40-80 минут в зависимости от того, как именно оно записано. "
        "Ещё мне можно прислать голосовую заметку из встроенного приложения айфона. \n \n"
        "Распознавание занимает от пары секунд до пары десятков секунд, в зависимости от длины аудио. \n \n"
        "Ничего не записываю и не храню."
    )
    await update.message.reply_text(message)


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


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages and audio files in private chats."""
    if update.message is None or update.message.from_user is None:
        return

    try:
        # Get voice or audio file
        file = update.message.voice or update.message.audio
        if file is None:
            return

        # Transcribe and bill user
        transcript = await transcribe(file, context, update.message.from_user.id)

        # Check if transcription failed due to insufficient balance
        if transcript is None:
            await update.message.reply_text(
                "У вас закончился лимит распознавания. Пополните счет звездами",
                reply_to_message_id=update.message.message_id,
                reply_markup=get_topup_keyboard(),
            )
            return

        # Send transcription, splitting into chunks if needed
        for i in range(0, len(transcript), MAX_MESSAGE_LENGTH):
            chunk = transcript[i : i + MAX_MESSAGE_LENGTH]
            await update.message.reply_text(
                chunk,
                reply_to_message_id=update.message.message_id,
            )

    except (RuntimeError, OSError, ValueError) as e:
        await update.message.reply_text(
            f"Sorry, transcription failed: {e}",
            reply_to_message_id=update.message.message_id,
        )


async def handle_group_mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bot mentions in groups that reply to voice messages."""
    if update.message is None or update.message.reply_to_message is None or update.message.from_user is None:
        return

    reply_msg = update.message.reply_to_message

    # Check if replied message contains voice or audio
    if not (reply_msg.voice or reply_msg.audio):
        await update.message.reply_text("Please reply to a voice message or audio file.")
        return

    try:
        # Get voice or audio file
        file = reply_msg.voice or reply_msg.audio
        if file is None:
            return

        # Transcribe and bill user (bill the requester, not the voice sender)
        transcript = await transcribe(file, context, update.message.from_user.id)

        # Check if transcription failed due to insufficient balance
        if transcript is None:
            await update.message.reply_text(
                "У вас закончился лимит распознавания. Пополните счет звездами",
                reply_markup=get_topup_keyboard(),
            )
            return

        # Send transcription as reply to the voice message
        for i in range(0, len(transcript), 4096):
            chunk = transcript[i : i + 4096]
            await reply_msg.reply_text(chunk)

    except (RuntimeError, OSError, ValueError) as e:
        await update.message.reply_text(f"Ошибочка вышла: {e}")


async def post_init(application: Application) -> None:
    """Initialize billing database on startup."""
    await init_billing_db()


async def post_shutdown(application: Application) -> None:
    """Logout from the Telegram API server on shutdown.

    This ensures clean migration between Telegram API servers (local or public).
    See: https://github.com/tdlib/telegram-bot-api#moving-a-bot-from-one-local-server-to-another
    """
    with contextlib.suppress(Exception):
        await application.bot.log_out()


def main() -> None:
    """Start the bot."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        msg = "BOT_TOKEN environment variable is not set"
        raise RuntimeError(msg)

    # Build application with optional local server configuration
    builder = Application.builder().token(token).post_init(post_init).post_shutdown(post_shutdown)

    # Configure custom Telegram API server if specified
    base_url = os.getenv("TELEGRAM_API_BASE_URL")
    if base_url:
        builder = builder.base_url(base_url)

    app = builder.build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("topup", topup))
    app.add_handler(CommandHandler("balance", balance))

    # Payment handlers
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(CallbackQueryHandler(topup_callback, pattern=r"^topup:\d+$"))

    # Voice/audio handlers for private chats
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & (filters.VOICE | filters.AUDIO),
            handle_voice,
        )
    )

    # Group mention handler for transcribing replied voice messages
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.REPLY & (filters.Entity("mention") | filters.Entity("text_mention")),
            handle_group_mention,
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()

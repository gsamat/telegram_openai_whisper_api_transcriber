import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from telegram import LabeledPrice
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, PreCheckoutQueryHandler, filters

from src.billing import bill, get_balance, hash_user_id, init_billing_db
from src.transcribe import transcribe_voice

if TYPE_CHECKING:
    from telegram import Audio, Update, Voice

load_dotenv()

MAX_MESSAGE_LENGTH = 4096
SECONDS_PER_STAR = 60 * 30  # 1 star = 30 minutes of transcription


async def transcribe(
    file: Voice | Audio,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> str:
    """Transcribe voice message and bill the user.

    Args:
        file: Voice or Audio object from Telegram
        context: Bot context for downloading files
        user_id: Telegram user ID to bill

    Returns:
        Transcribed text

    Raises:
        Exception: If transcription fails
    """
    # Transcribe using OpenAI Whisper
    transcript = await transcribe_voice(file, context)

    # Bill user for transcription
    user_hash = hash_user_id(user_id)
    await bill(user_hash, -file.duration, "transcribing")

    return transcript


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    if update.message is None:
        return
    await update.message.reply_text("Hello! Welcome to the bot. Send me a voice message and I'll transcribe it for you.")


async def topup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /topup command - send invoice for Telegram Stars.

    Usage: /topup <amount>
    Example: /topup 5 (to purchase 5 stars worth of transcription credits)
    """
    if update.message is None:
        return

    # Parse amount from command args
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "Please specify the amount of stars to purchase.\n"
            f"Usage: /topup <amount>\n"
            f"Example: /topup 5\n\n"
            f"Rate: 1 star = {SECONDS_PER_STAR // 60} minutes of transcription"
        )
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
        description=f"Top up your balance with {minutes} minutes of voice transcription",
        payload="topup",
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice("Transcription credits", stars)],
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /balance command - show user's current balance."""
    if update.message is None:
        return

    user_hash = hash_user_id(update.message.from_user.id)
    current_balance = await get_balance(user_hash)

    minutes = int(current_balance // 60)
    seconds = int(current_balance % 60)

    await update.message.reply_text(f"Your balance: {minutes} min {seconds} sec")


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pre-checkout query - verify payment before processing."""
    query = update.pre_checkout_query

    # Verify payload matches our invoice
    if query.invoice_payload != "topup":
        await query.answer(ok=False, error_message="Invalid payment request.")
        return

    # Approve the payment
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle successful payment - credit user's balance."""
    if update.message is None or update.message.successful_payment is None:
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
    await update.message.reply_text(
        f"Thank you for your payment! ✅\n\nCredited: {minutes} minutes ({credited_seconds} seconds) of transcription time.\nCost: {stars} ⭐"
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages and audio files in private chats."""
    if update.message is None:
        return

    try:
        # Get voice or audio file
        file = update.message.voice or update.message.audio
        if file is None:
            return

        # Transcribe and bill user
        transcript = await transcribe(file, context, update.message.from_user.id)

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
    if update.message is None or update.message.reply_to_message is None:
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

        # Send transcription as reply to the voice message
        for i in range(0, len(transcript), 4096):
            chunk = transcript[i : i + 4096]
            await reply_msg.reply_text(chunk)

    except (RuntimeError, OSError, ValueError) as e:
        await update.message.reply_text(f"Sorry, transcription failed: {e}")


async def post_init(application: Application) -> None:
    """Initialize billing database on startup."""
    await init_billing_db()


def main() -> None:
    """Start the bot."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        msg = "BOT_TOKEN environment variable is not set"
        raise RuntimeError(msg)

    app = Application.builder().token(token).post_init(post_init).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("topup", topup))
    app.add_handler(CommandHandler("balance", balance))

    # Payment handlers
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

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

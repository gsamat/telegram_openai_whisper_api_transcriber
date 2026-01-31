import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from src.billing import bill, hash_user_id, init_billing_db
from src.transcribe import transcribe_voice

if TYPE_CHECKING:
    from telegram import Audio, Update, Voice

load_dotenv()

MAX_MESSAGE_LENGTH = 4096


async def transcribe(
    file: "Voice | Audio",
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

    except Exception as e:
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

    except Exception as e:
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

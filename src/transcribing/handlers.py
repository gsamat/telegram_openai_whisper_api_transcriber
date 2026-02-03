"""Transcription handlers for voice and audio messages."""

from datetime import timedelta
from typing import TYPE_CHECKING

from telegram.ext import Application, MessageHandler, filters

from billing import bill, do_billing_stuff, get_topup_keyboard, hash_user_id
from config import MAX_MESSAGE_LENGTH

from .whisper import transcribe_voice

if TYPE_CHECKING:
    from telegram import Audio, Update, Voice
    from telegram.ext import ContextTypes


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
    # file.duration can be int (seconds) or timedelta in python-telegram-bot
    duration = file.duration.total_seconds() if isinstance(file.duration, timedelta) else float(file.duration)
    user_hash = hash_user_id(user_id)
    await bill(user_hash, -duration, "transcribing")

    return transcript


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages and audio files in private chats."""
    if update.message is None or update.message.from_user is None:
        return

    try:
        # Get voice or audio file
        file = update.message.voice or update.message.audio
        if file is None:
            return

        # Check balance before transcribing
        balance = await do_billing_stuff(update.message.from_user.id)
        if balance < 0:
            await update.message.reply_text(
                "У вас закончился лимит распознавания. Пополните счет звездами",
                reply_to_message_id=update.message.message_id,
                reply_markup=get_topup_keyboard(),
            )
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

        # Check balance before transcribing
        balance = await do_billing_stuff(update.message.from_user.id)
        if balance < 0:
            await update.message.reply_text(
                "У вас закончился лимит распознавания. Пополните счет звездами",
                reply_markup=get_topup_keyboard(),
            )
            return

        # Transcribe and bill user (bill the requester, not the voice sender)
        transcript = await transcribe(file, context, update.message.from_user.id)

        # Send transcription as reply to the voice message
        for i in range(0, len(transcript), 4096):
            chunk = transcript[i : i + 4096]
            await reply_msg.reply_text(chunk)

    except (RuntimeError, OSError, ValueError) as e:
        await update.message.reply_text(f"Ошибочка вышла: {e}")


def register_handlers(app: Application) -> None:
    """Register all transcription-related handlers with the application.

    Args:
        app: Telegram Application instance
    """
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

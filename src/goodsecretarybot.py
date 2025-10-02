from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import asyncio
import io
import magic
import os
import time
import hashlib
import sentry_sdk
from dotenv import load_dotenv

import db
import messages
from transcribe import get_transcription_client

MAX_MESSAGE_LENGTH = 4096

load_dotenv()

telegram_token = os.environ.get('TELEGRAM_TOKEN')
bot_name = os.environ.get('BOT_NAME')
telegram_bot_api_url = os.environ.get('TELEGRAM_BOT_API_URL')
transcription_engine = os.environ.get('TRANSCRIPTION_ENGINE', 'openai')
available_seconds = int(os.environ.get('AVAILABLE_MINUTES')) * 60


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(messages.start_message(available_seconds))


async def handle_voice(update: Update, context: CallbackContext) -> None:
    hashed_user_id = hashlib.sha256(str(update.message.from_user.id).encode()).hexdigest()
    sentry_sdk.set_user({"id": hashed_user_id})
    file_duration = update.message.voice.duration if update.message.voice else update.message.audio.duration

    used_month_seconds = await db.get_used_month_seconds(hashed_user_id)
    if used_month_seconds + file_duration > available_seconds:
        await update.message.reply_text(messages.limit_exceeded_message(used_month_seconds, available_seconds))
        return

    file_handle = None
    try:
        if update.message.voice:
            file_handle = await context.bot.get_file(update.message.voice.file_id)
        elif update.message.audio:
            file_handle = await context.bot.get_file(update.message.audio.file_id)
        file_data = io.BytesIO()
        await file_handle.download_to_memory(file_data)
        file_data.seek(0)
        mime_type = magic.from_buffer(file_data.read(2048), mime=True)
        file_data.seek(0)
        start_time = time.time()
        transcript = client.transcribe(file_data, mime_type)
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        transcription_time = time.time() - start_time
        for i in range(0, len(transcript), MAX_MESSAGE_LENGTH):
                    await update.message.reply_text(transcript[i:i+MAX_MESSAGE_LENGTH], reply_to_message_id=update.message.message_id)
        await db.insert_transcription_log(hashed_user_id, file_duration, transcription_time, current_time)
    except Exception as e:
        await update.message.reply_text(f"Ошибочка: {e}", reply_to_message_id=update.message.message_id)
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        await db.insert_transcription_log(hashed_user_id, file_duration, -1, current_time)
        sentry_sdk.capture_exception(e)
    finally:
        if file_handle and os.path.exists(file_handle.file_path):
            os.remove(file_handle.file_path)


async def handle_command(update: Update, context: CallbackContext) -> None:
    # If the bot is mentioned in a reply to a voice message
    if update.message.reply_to_message and (update.message.reply_to_message.voice or update.message.reply_to_message.audio):
        voice_message = update.message.reply_to_message
        voice_update = type('obj', (object,), {'message' : voice_message})
        await handle_voice(voice_update, context)


async def check_available_time(update: Update, context: CallbackContext) -> None:
    hashed_user_id = hashlib.sha256(str(update.message.from_user.id).encode()).hexdigest()
    used_month_seconds = await db.get_used_month_seconds(hashed_user_id)
    await update.message.reply_text(messages.check_available_time_message(used_month_seconds, available_seconds))


def main():
    application = None
    if telegram_bot_api_url:
        application = Application.builder().token(telegram_token).base_url(telegram_bot_api_url).local_mode(True).build()
    else:
        application = Application.builder().token(telegram_token).build()

    start_handler = CommandHandler('start', start)
    voice_handler = MessageHandler(filters.ChatType.PRIVATE & (filters.VOICE | filters.AUDIO), handle_voice)
    text_handler = CommandHandler('text', handle_command)
    mention_handler = MessageHandler(filters.ChatType.GROUPS & filters.Mention(bot_name), handle_command)
    check_available_time_handler = CommandHandler('stats', check_available_time)

    application.add_handler(start_handler)
    application.add_handler(voice_handler)
    application.add_handler(text_handler)
    application.add_handler(mention_handler)
    application.add_handler(check_available_time_handler)

    application.run_polling()

if __name__ == '__main__':
    if os.environ.get('SENTRY_DSN'):
        sentry_sdk.init(
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            traces_sample_rate=1.0,
            # Set profiles_sample_rate to 1.0 to profile 100%
            # of sampled transactions.
            # We recommend adjusting this value in production.
            profiles_sample_rate=1.0,
        )
    client = get_transcription_client(transcription_engine)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.generate_db())
    main()

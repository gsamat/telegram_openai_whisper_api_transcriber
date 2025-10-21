import sentry_sdk
import os

from aiogram.utils.formatting import BlockQuote, Pre
from bot.bot_init import bot
from config import settings
import bot.messages as messages
from bot.services.transcribe import transcription_client
from bot.services import db
import time


async def handle_audio_file(message, hashed_user_id, file_duration, file_id, mime_type):
    file_info = None
    try:
        user, check_result = await db.prepare_user_for_transcription(
            hashed_user_id, file_duration
        )
        if check_result == "exceeded":
            await message.reply(
                messages.limit_exceeded_message(
                    user.left_free_seconds + user.left_purchased_seconds,
                    settings.AVAILABLE_SECONDS,
                )
            )
            return
        elif check_result == "show_warning":
            await message.reply(
                messages.limit_warning_message(
                    user.left_free_seconds + user.left_purchased_seconds,
                    settings.AVAILABLE_SECONDS,
                )
            )
        msg = await message.reply("Распознаю...")

        file_info = await bot.get_file(file_id)
        file = await bot.download_file(file_info.file_path)

        start_time = time.time()
        transcript = await transcription_client.transcribe(file, mime_type)
        transcription_time = time.time() - start_time

        if len(transcript) > settings.MAX_MESSAGE_LENGTH:
            await msg.edit_text(**BlockQuote(transcript[:settings.MAX_MESSAGE_LENGTH]).as_kwargs())
            for i in range(settings.MAX_MESSAGE_LENGTH, len(transcript), settings.MAX_MESSAGE_LENGTH):
                await message.reply(**BlockQuote(transcript[i : i + settings.MAX_MESSAGE_LENGTH]).as_kwargs())
        else:
            await msg.edit_text(**BlockQuote(transcript).as_kwargs())

        await db.process_user_transcription(user, file_duration, transcription_time)
        await db.insert_transcription_log(user, file_duration, transcription_time)
    except Exception as e:
        await msg.edit_text(**Pre(f"Ошибочка: {e[:settings.MAX_MESSAGE_LENGTH]}").as_kwargs())
        sentry_sdk.capture_exception(e)
        user, _ = await db.get_or_create_user(hashed_user_id)
        await db.insert_transcription_log(user, file_duration, -1)
    finally:
        if file_info and os.path.exists(file_info.file_path):
            os.remove(file_info.file_path)

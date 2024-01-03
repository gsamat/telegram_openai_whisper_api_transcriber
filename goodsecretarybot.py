import hashlib
import io
import os
import time

import aiosqlite
import magic
import sentry_sdk
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler, filters, MessageHandler


telegram_token = os.environ.get('TELEGRAM_TOKEN')

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Привет! Я распознаю голосовые сообщения. Вы кидаете мне голосовое, я в ответ возвращаю его текстовую версию. \n \nЕсть ограничение на максимальную длину голосового — около 40-80 минут в зависимости от того, как именно оно записано. Ещё мне можно прислать голосовую заметку из встроенного приложения айфона. \n \nРаспознавание занимает от пары секунд до пары десятков секунд, в зависимости от длины аудио. \n \nНичего не записываю и не храню.')

async def transcribe_voice(update: Update, context: CallbackContext) -> None:

    hashed_user_id = hashlib.sha256(str(update.message.from_user.id).encode()).hexdigest()
    sentry_sdk.set_user({'id': hashed_user_id})
    file_duration = update.message.voice.duration if update.message.voice else update.message.audio.duration

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
        file = ('file', file_data.getvalue(), mime_type)
        start_time = time.time()
        transcript = client.audio.transcriptions.create(
          model='whisper-1',
          file=file,
          response_format='text',
        )
        transcription_time = time.time() - start_time
        await update.message.reply_text(transcript, reply_to_message_id=update.message.message_id)
        print(f'{hashed_user_id}, {file_duration}, {transcription_time}')
        async with aiosqlite.connect('transcriptions.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS transcriptions (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                hashed_user_id TEXT,
                                audio_duration INTEGER,
                                transcription_time REAL
                            )''')
            await db.execute('INSERT INTO transcriptions (hashed_user_id, audio_duration, transcription_time) VALUES (?, ?, ?)',
                             (hashed_user_id, file_duration, transcription_time))
            await db.commit()

    except Exception as e:
        await update.message.reply_text(f'Ошибочка: {e}', reply_to_message_id=update.message.message_id)
        async with aiosqlite.connect('transcriptions.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS transcriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        hashed_user_id TEXT,
                        audio_duration INTEGER,
                        transcription_time REAL
                    )''')
            await db.execute('INSERT INTO transcriptions (hashed_user_id, audio_duration, transcription_time) VALUES (?, ?, ?)',
                             (hashed_user_id, file_duration, -1))
            await db.commit()
        sentry_sdk.capture_exception(e)

def main():
    application = Application.builder().token(telegram_token).build()

    start_handler = CommandHandler('start', start)
    voice_handler = MessageHandler(filters.VOICE | filters.AUDIO, transcribe_voice)

    application.add_handler(start_handler)
    application.add_handler(voice_handler)

    application.run_polling()

if __name__ == '__main__':
    sentry_sdk.init(
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )
    client = OpenAI()
    main()

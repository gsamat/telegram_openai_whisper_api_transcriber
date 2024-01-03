from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from urllib.parse import urlparse
import asyncio
import io
import magic
import os
import requests

telegram_token = os.environ.get('TELEGRAM_TOKEN')

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Привет! Я распознаю голосовые сообщения. Вы кидаете мне голосовое, я в ответ возвращаю его текстовую версию. \n \nЕсть ограничение на максимальную длину голосового — около 40-80 минут в зависимости от того, как именно оно записано. Ещё мне можно прислать голосовую заметку из встроенного приложения айфона. \n \nРаспознавание занимает от пары секунд до пары десятков секунд, в зависимости от длины аудио. \n \nНичего не записываю и не храню.')

async def transcribe_voice(update: Update, context: CallbackContext) -> None:
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
        transcript = client.audio.transcriptions.create(
          model="whisper-1", 
          file=file, 
          response_format="text"
        )
        await update.message.reply_text(transcript, reply_to_message_id=update.message.message_id)
    except Exception as e:
        await update.message.reply_text(f"Ошибочка: {e}", reply_to_message_id=update.message.message_id)
    

def main():
    application = Application.builder().token(telegram_token).build()

    start_handler = CommandHandler('start', start)
    voice_handler = MessageHandler(filters.VOICE | filters.AUDIO, transcribe_voice)

    application.add_handler(start_handler)
    application.add_handler(voice_handler)

    application.run_polling()

if __name__ == '__main__': 

    client = OpenAI()
    main()

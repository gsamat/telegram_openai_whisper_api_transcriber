from urllib.parse import urlparse
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import requests
import asyncio
import os
import io
from openai import OpenAI
import magic

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hi! Send me a voice message.')

async def transcribe_voice(update: Update, context: CallbackContext) -> None:
    if update.message.voice:
        file_handle = await context.bot.get_file(update.message.voice.file_id)
    elif update.message.audio:
        file_handle = await context.bot.get_file(update.message.audio.file_id)
    filename = os.path.basename(urlparse(file_handle.file_path).path)
    print(filename)
    file_data = io.BytesIO()
    await file_handle.download_to_memory(file_data)
    file_data.seek(0)
    mime_type = magic.from_buffer(file_data.read(2048), mime=True)
    file_data.seek(0)
    print('ours: ', mime_type)
    file = ('file', file_data.getvalue(), mime_type)

    transcript = ''

    try:
        transcript = client.audio.transcriptions.create(
          model="whisper-1", 
          file=file, 
          response_format="text"
        )
        await update.message.reply_text(transcript, reply_to_message_id=update.message.message_id)
    except Exception as e:
        await update.message.reply_text(f"Sorry, I couldn't transcribe that. This is the exception: {e}", reply_to_message_id=update.message.message_id)
    

def main():
    application = Application.builder().token("***REMOVED***").build()


    start_handler = CommandHandler('start', start)
    voice_handler = MessageHandler(filters.VOICE | filters.AUDIO, transcribe_voice)

    application.add_handler(start_handler)
    application.add_handler(voice_handler)

    application.run_polling()

if __name__ == '__main__': 

    client = OpenAI(api_key='***REMOVED***')
    main()

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import requests
import asyncio
import os
from openai import OpenAI

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hi! Send me a voice message.')

async def transcribe_voice(update: Update, context: CallbackContext) -> None:
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    file_data = await voice_file.download_to_memory()
    
    transcript = ''

    try:
        transcript = client.audio.transcriptions.create(
          model="whisper-1", 
          file=file_data, 
          response_format="text"
        )
        await update.message.reply_text(transcript)
    except Exception as e:
        await update.message.reply_text(f"Sorry, I couldn't transcribe that. This is the exception: {e}")        
    

def main():
    application = Application.builder().token("***REMOVED***").build()


    start_handler = CommandHandler('start', start)
    voice_handler = MessageHandler(filters.VOICE, transcribe_voice)

    application.add_handler(start_handler)
    application.add_handler(voice_handler)

    application.run_polling()

if __name__ == '__main__': 

    client = OpenAI(api_key='***REMOVED***')
    main()

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import requests
import asyncio
import os

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hi! Send me a voice message.')

async def transcribe_voice(update: Update, context: CallbackContext) -> None:
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    voice_file.download('voice.ogg')

    with open('voice.ogg', 'rb') as f:
        response = requests.post(
            "YOUR_WHISPER_API_ENDPOINT",  # Replace with the actual Whisper API endpoint
            headers={"Authorization": "Bearer ***REMOVED***"},
            files={"file": f}
        )

    if response.status_code == 200:
        transcription = response.json().get("transcription")
        await update.message.reply_text(transcription)
    else:
        await update.message.reply_text("Sorry, I couldn't transcribe that.")

    os.remove('voice.ogg')

def main():
    application = Application.builder().token("***REMOVED***").build()

    start_handler = CommandHandler('start', start)
    voice_handler = MessageHandler(filters.VOICE, transcribe_voice)

    application.add_handler(start_handler)
    application.add_handler(voice_handler)

    application.run_polling()

if __name__ == '__main__': 
    main()

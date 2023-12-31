import os
import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, filters

def start(update, context):
    update.message.reply_text('Hi! I am a Good Secretary Bot. Send me your voice message and I will transcribe them for you using OpenAI Whisper API. Messages are not stored and not logged in this bot at any point.')

def transcribe_voice(update, context):
    voice_file = update.message.voice.get_file()
    voice_file.download('voice.ogg')

    # Send the file to OpenAI's Whisper API
    with open('voice.ogg', 'rb') as f:
        response = requests.post(
            "https://api.openai.com/v1/whisper/transcribe",
            headers={"Authorization": f"Bearer ***REMOVED***"},
            files={"file": f}
        )

    if response.status_code == 200:
        transcription = response.json().get("transcription")
        update.message.reply_text(transcription)
    else:
        update.message.reply_text("Sorry, I couldn't transcribe that.")

    os.remove('voice.ogg')

def main():
    updater = Updater("***REMOVED***")
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.voice, transcribe_voice))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
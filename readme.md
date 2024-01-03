# telegram_openai_whisper_api_transcriber

Telegram bot to transcribe voice messages using OpenAI Whisper API

## Installation

pip3 install -r requirements.txt
sudo apt install libmagic1

## Running

TELEGRAM_TOKEN='your telegram token here' OPENAI_API_KEY='your openai api key here' python3 goodsecretarybot.py

## Using Docker

1. Change `TELEGRAM_TOKEN` and `OPENAI_API_KEY` variables in `Dockerfile`.
2. `docker build -t transcriber .` 
3. `docker run transcriber`
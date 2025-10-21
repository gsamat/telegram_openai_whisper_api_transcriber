# telegram_openai_whisper_api_transcriber

Telegram bot to transcribe voice messages using OpenAI API or ElevenLabs API

## Installation

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Fill .env file with correct variables.

## Running

1. `uv run src/manage.py migrate`
2. `uv run src/manage.py runbot`

## Using Docker compose (recommended way)

Added local telegram-bot-api service for handling files larger than 20MB.

1. `cp .env.example .env` and fill .env file with correct variables.
2. `./logout.sh` - [logout](https://github.com/tdlib/telegram-bot-api#moving-a-bot-to-a-local-server) from telegram bot api server.
3. `docker compose up -d` - it will very long time to build telegram-bot-api image.

## Switch transcription engine

You should set `TRANSCRIPTION_ENGINE` variable in .env file.

Available engines:

- `openai-whisper`
- `openai-gpt-4o-mini-transcribe`
- `elevenlabs-scribe_v1`
- `gemini-2.5-flash`

Default engine is `openai-gpt-4o-mini-transcribe`.

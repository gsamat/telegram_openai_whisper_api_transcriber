"""Telegram bot for voice transcription - main entry point."""

import contextlib
import os

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler

import billing
import transcribing
from billing import init_billing_db

load_dotenv()


async def start(update, context) -> None:
    """Handle the /start command."""
    if update.message is None:
        return
    message = (
        "Привет! Я распознаю голосовые сообщения. Вы кидаете мне голосовое, я в ответ возвращаю его текстовую версию. \n \n"
        "Есть ограничение на максимальную длину голосового — около 40-80 минут в зависимости от того, как именно оно записано. "
        "Ещё мне можно прислать голосовую заметку из встроенного приложения айфона. \n \n"
        "Распознавание занимает от пары секунд до пары десятков секунд, в зависимости от длины аудио. \n \n"
        "Ничего не записываю и не храню."
    )
    await update.message.reply_text(message)


async def post_init(application: Application) -> None:
    """Initialize billing database on startup."""
    await init_billing_db()


async def post_shutdown(application: Application) -> None:
    """Logout from the Telegram API server on shutdown.

    This ensures clean migration between Telegram API servers (local or public).
    See: https://github.com/tdlib/telegram-bot-api#moving-a-bot-from-one-local-server-to-another
    """
    with contextlib.suppress(Exception):
        await application.bot.log_out()


def main() -> None:
    """Start the bot."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        msg = "BOT_TOKEN environment variable is not set"
        raise RuntimeError(msg)

    # Build application with optional local server configuration
    builder = Application.builder().token(token).post_init(post_init).post_shutdown(post_shutdown)

    # Configure custom Telegram API server if specified
    base_url = os.getenv("TELEGRAM_API_BASE_URL")
    if base_url:
        builder = builder.base_url(base_url)

    app = builder.build()

    # Register /start command
    app.add_handler(CommandHandler("start", start))

    # Register billing handlers
    billing.register_handlers(app)

    # Register transcribing handlers
    transcribing.register_handlers(app)

    app.run_polling()


if __name__ == "__main__":
    main()

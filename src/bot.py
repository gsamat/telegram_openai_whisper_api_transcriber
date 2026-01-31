import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, ContextTypes

if TYPE_CHECKING:
    from telegram import Update

load_dotenv()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    if update.message is None:
        return
    await update.message.reply_text("Hello! Welcome to the bot.")


def main() -> None:
    """Start the bot."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        msg = "BOT_TOKEN environment variable is not set"
        raise RuntimeError(msg)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()


if __name__ == "__main__":
    main()

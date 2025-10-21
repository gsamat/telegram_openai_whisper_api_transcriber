import asyncio

from django.core.management.base import BaseCommand
from bot.bot_init import run_bot
from config import settings
import sentry_sdk


class Command(BaseCommand):
    help = "Run the bot"

    def handle(self, *args, **options):
        asyncio.run(self.main())

    async def main(self):
        if settings.SENTRY_DSN:
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                traces_sample_rate=1.0,
                profiles_sample_rate=1.0,
            )
        print("Bot started")
        await run_bot()

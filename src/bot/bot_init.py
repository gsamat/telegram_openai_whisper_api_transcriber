from aiogram import Bot, Dispatcher

from config import settings


if settings.TELEGRAM_BOT_API_URL:
    from aiogram.client.session.aiohttp import AiohttpSession
    from aiogram.client.telegram import TelegramAPIServer

    session = AiohttpSession(
        api=TelegramAPIServer.from_base(settings.TELEGRAM_BOT_API_URL, is_local=True)
    )
    bot = Bot(token=settings.TELEGRAM_TOKEN, session=session)
else:
    bot = Bot(token=settings.TELEGRAM_TOKEN)
dp = Dispatcher()


def setup_handlers(dp: Dispatcher) -> None:
    from bot import handlers

    dp.include_routers(
        handlers.util.router,
        handlers.voice.router,
        handlers.payment.router,
    )


async def run_bot() -> None:
    setup_handlers(dp)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

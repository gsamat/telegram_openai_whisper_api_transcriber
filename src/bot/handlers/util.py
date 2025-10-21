import hashlib

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import settings
from bot import messages
from bot.services import db

router = Router()


@router.message(Command("start"))
async def start(message: Message):
    await message.reply(messages.start_message(settings.AVAILABLE_SECONDS))


@router.message(Command("stats"))
async def stats(message: Message):
    hashed_user_id = hashlib.sha256(str(message.from_user.id).encode()).hexdigest()
    user, _ = await db.get_or_create_user(hashed_user_id)
    await message.reply(
        messages.stats_message(
            user.left_free_seconds,
            user.left_purchased_seconds,
            settings.AVAILABLE_SECONDS,
            user.last_free_reset_at,
        )
    )

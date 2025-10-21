import hashlib

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import LabeledPrice
from aiogram.utils.formatting import Text, Code


from bot.services import db
from bot import messages
from config import settings

router = Router()


@router.message(Command("payment"))
async def payment(message: Message, command: CommandObject):
    if (
        command.args is None
        or not command.args.isdigit()
        or not 1 <= int(command.args) <= 2500
    ):
        await message.reply(
            **Text(
                "Пожалуйста, вызовите команду ",
                Code("/payment N"),
                " с количеством звезд от 1 до 2500",
            ).as_kwargs()
        )
        return
    amount = int(command.args)
    amount_in_minutes = amount * int(settings.CURRENCY_RATE_SECONDS / 60)
    hashed_user_id = hashlib.sha256(str(message.from_user.id).encode()).hexdigest()
    user, _ = await db.get_or_create_user(hashed_user_id)
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Оплатить {amount} XTR", pay=True)
    builder.adjust(1)

    prices = [LabeledPrice(label="XTR", amount=amount)]
    await message.answer_invoice(
        title="Покупка минут распознавания",
        description=f"Ты покупаешь {amount_in_minutes} мин. распознавания",
        prices=prices,
        provider_token="",
        payload=f"{amount}_stars",
        currency="XTR",
        reply_markup=builder.as_markup(),
    )


@router.pre_checkout_query()
async def on_pre_checkout_query(
    pre_checkout_query: PreCheckoutQuery,
):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(
    message: Message,
):
    hashed_user_id = hashlib.sha256(str(message.from_user.id).encode()).hexdigest()
    user, _ = await db.get_or_create_user(hashed_user_id)
    await db.make_payment(
        user,
        message.successful_payment.telegram_payment_charge_id,
        message.successful_payment.total_amount,
    )
    await message.reply(
        messages.payment_successful_message(
            message.successful_payment.total_amount
            * int(settings.CURRENCY_RATE_SECONDS / 60)
        )
    )


@router.message(Command("paysupport"))
async def paysupport(message: Message):
    await message.reply(messages.paysupport_message(settings.SUPPORT_USERNAME))

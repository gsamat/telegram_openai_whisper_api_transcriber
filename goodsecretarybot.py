import io
import os

import sentry_sdk
from dotenv import load_dotenv
from openai import OpenAI
from telegram import LabeledPrice, Update
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from billing import CREDITS_PER_EUR, decrement_balance, increment_balance
from transcriber import (
    detect_mime_type,
    hash_user_id,
    log_transcription,
    transcribe_audio,
)

load_dotenv()

MAX_MESSAGE_LENGTH = 4096

telegram_token = os.environ.get("TELEGRAM_TOKEN")
bot_name = os.environ.get("BOT_NAME")
redsys_token = os.environ.get("REDSYS_TOKEN")


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Привет! Я распознаю голосовые сообщения. Вы кидаете мне голосовое, я в ответ возвращаю его текстовую версию. \n \nЕсть ограничение на максимальную длину голосового — около 40-80 минут в зависимости от того, как именно оно записано. Ещё мне можно прислать голосовую заметку из встроенного приложения айфона. \n \nРаспознавание занимает от пары секунд до пары десятков секунд, в зависимости от длины аудио. \n \nНичего не записываю и не храню."
    )


async def handle_voice(update: Update, context: CallbackContext) -> None:
    """

    Downloads the audio from Telegram, sends it to OpenAI Whisper API
    for transcription, and replies with the transcribed text. Logs
    transcription statistics to the database.

    On error, sends an error message to the user, logs the failure
    to the database (with transcription_time=-1), and reports to Sentry.
    """
    hashed_user_id = hash_user_id(update.message.from_user.id)
    sentry_sdk.set_user({"id": hashed_user_id})
    file_duration = (
        update.message.voice.duration
        if update.message.voice
        else update.message.audio.duration
    )

    try:
        if update.message.voice:
            file_handle = await context.bot.get_file(update.message.voice.file_id)
        elif update.message.audio:
            file_handle = await context.bot.get_file(update.message.audio.file_id)
        file_data = io.BytesIO()
        await file_handle.download_to_memory(file_data)

        mime_type = detect_mime_type(file_data)
        transcript, transcription_time = transcribe_audio(file_data, mime_type)

        for i in range(0, len(transcript), MAX_MESSAGE_LENGTH):
            await update.message.reply_text(
                transcript[i : i + MAX_MESSAGE_LENGTH],
                reply_to_message_id=update.message.message_id,
            )
        print(f"{hashed_user_id}, {file_duration}, {transcription_time}")
        await decrement_balance(
            hashed_user_id, transcription_time, source="usage_charge"
        )
        await log_transcription(hashed_user_id, file_duration, transcription_time)

    except Exception as e:
        await update.message.reply_text(
            f"Ошибочка: {e}", reply_to_message_id=update.message.message_id
        )
        await log_transcription(hashed_user_id, file_duration, transcription_time=-1)
        sentry_sdk.capture_exception(e)


async def handle_command(update: Update, context: CallbackContext) -> None:
    """Handle /text command and @mentions in group chats.

    When the bot is mentioned or /text is used in reply to a voice
    message or audio file, triggers transcription of that message.
    """
    # If the bot is mentioned in a reply to a voice message
    if update.message.reply_to_message and (
        update.message.reply_to_message.voice or update.message.reply_to_message.audio
    ):
        voice_message = update.message.reply_to_message
        voice_update = type("obj", (object,), {"message": voice_message})
        await handle_voice(voice_update, context)


async def topup(update: Update, context: CallbackContext) -> None:
    """Handle /topup <amount> command - sends invoice to user."""
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Использование: /topup <сумма> (например, /topup 5)"
        )
        return

    amount = int(context.args[0])
    if amount < 1:
        await update.message.reply_text("Сумма должна быть не менее 1 EUR")
        return

    credits = amount * CREDITS_PER_EUR
    chat_id = update.message.chat_id
    title = f"Пополнение на {credits} кредитов"
    description = (
        f"Пополнение баланса на {credits} кредитов ({credits} секунд транскрибации)"
    )
    payload = f"{update.message.from_user.id}"
    currency = "EUR"
    prices = [LabeledPrice("Кредиты", amount * 100)]  # amount in cents

    await context.bot.send_invoice(
        chat_id,
        title,
        description,
        payload,
        currency,
        prices,
        provider_token=redsys_token,
    )


async def precheckout_callback(update: Update, context: CallbackContext) -> None:
    """Handle pre-checkout query - must respond within 10 seconds."""
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: CallbackContext) -> None:
    """Handle successful payment - add credits to user balance."""
    payment = update.message.successful_payment
    hashed_user_id = hash_user_id(update.message.from_user.id)

    # Amount is in cents, convert EUR to credits
    amount_eur = payment.total_amount / 100
    credits = amount_eur * CREDITS_PER_EUR

    await increment_balance(
        hashed_user_id=hashed_user_id,
        amount=credits,
        source="telegram_payment",
        telegram_payment_id=payment.telegram_payment_charge_id,
    )

    await update.message.reply_text(
        f"Оплата прошла успешно! Добавлено {int(credits)} кредитов на ваш баланс."
    )


def main():
    application = Application.builder().token(telegram_token).build()

    start_handler = CommandHandler("start", start)
    voice_handler = MessageHandler(
        filters.ChatType.PRIVATE & (filters.VOICE | filters.AUDIO), handle_voice
    )
    text_handler = CommandHandler("text", handle_command)
    mention_handler = MessageHandler(
        filters.ChatType.GROUPS & filters.Mention(bot_name), handle_command
    )
    topup_handler = CommandHandler("topup", topup)
    precheckout_handler = PreCheckoutQueryHandler(precheckout_callback)
    successful_payment_handler = MessageHandler(
        filters.SUCCESSFUL_PAYMENT, successful_payment_callback
    )

    application.add_handler(start_handler)
    application.add_handler(voice_handler)
    application.add_handler(text_handler)
    application.add_handler(mention_handler)
    application.add_handler(topup_handler)
    application.add_handler(precheckout_handler)
    application.add_handler(successful_payment_handler)

    application.run_polling()


if __name__ == "__main__":
    sentry_sdk.init(
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )
    main()

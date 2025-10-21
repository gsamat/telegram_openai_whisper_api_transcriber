import math
from datetime import datetime, timedelta


def start_message(available_seconds: int) -> str:
    return START_MESSAGE.format(available_minutes=math.ceil(available_seconds / 60))


START_MESSAGE = """
Привет! Я распознаю голосовые сообщения. Вы кидаете мне голосовое, я в ответ возвращаю его текстовую версию.

Ещё мне можно прислать голосовую заметку из встроенного приложения айфона.

Распознавание занимает от пары секунд до пары десятков секунд, в зависимости от длины аудио.

Ничего не записываю и не храню.

Каждый месяц тебе доступно {available_minutes} минут на распознавание.

Полезные команды:
/stats - проверить, сколько минут осталось.
/payment N - купить дополнительные минуты.
"""


def stats_message(
    left_free_seconds: int,
    left_purchased_seconds: int,
    available_seconds: int,
    last_free_reset_at: datetime,
) -> str:
    return STATS_MESSAGE.format(
        left_free_minutes=math.ceil(left_free_seconds / 60),
        left_purchased_minutes=math.ceil(left_purchased_seconds / 60),
        available_minutes=math.ceil(available_seconds / 60),
        next_free_reset_at=(last_free_reset_at + timedelta(days=30)).strftime(
            "%d.%m.%Y"
        ),
    )


STATS_MESSAGE = """
Баланс минут:
Бесплатные: {left_free_minutes}
Купленные: {left_purchased_minutes}

Твои бесплатные минуты обновятся {next_free_reset_at}.
"""


def limit_exceeded_message(left_free_seconds: int, available_seconds: int) -> str:
    return LIMIT_EXCEEDED_MESSAGE.format(
        left_free_minutes=math.ceil(left_free_seconds / 60),
        available_minutes=math.ceil(available_seconds / 60),
    )


LIMIT_EXCEEDED_MESSAGE = """
На этот месяц бесплатные минуты закончились.

Использовано: {left_free_minutes}/{available_minutes} минут.

Ты можешь приобрести дополнительные минуты командой /payment N.
"""


def limit_warning_message(left_free_seconds: int, available_seconds: int) -> str:
    return LIMIT_WARNING_MESSAGE.format(
        left_free_minutes=math.ceil(left_free_seconds / 60),
        available_minutes=math.ceil(available_seconds / 60),
    )


LIMIT_WARNING_MESSAGE = """
У тебя заканчиваются бесплатные минуты.

Использовано: {left_free_minutes}/{available_minutes} минут.
"""


def paysupport_message(support_username: str) -> str:
    return PAYSUPPORT_MESSAGE.format(support_username=support_username)


PAYSUPPORT_MESSAGE = """
Если возникли проблемы с покупкой, напиши мне: {support_username}
"""


def payment_successful_message(minutes: int) -> str:
    return PAYMENT_SUCCESSFUL_MESSAGE.format(minutes=minutes)


PAYMENT_SUCCESSFUL_MESSAGE = """
Платёж успешно проведён.

Тебе начислено {minutes} мин. распознавания.
"""

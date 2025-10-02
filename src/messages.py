import math

def start_message(available_seconds: int) -> str:
    return START_MESSAGE.format(available_minutes=math.ceil(available_seconds / 60))


def check_available_time_message(used_month_seconds: int, available_seconds: int) -> str:
    return CHECK_AVAILABLE_MINUTES_MESSAGE.format(used_month_minutes=math.ceil(used_month_seconds / 60), available_minutes=math.ceil(available_seconds / 60))


def error_message(error: str) -> str:
    return ERROR_MESSAGE.format(error=error)


def limit_exceeded_message(used_month_seconds: int, available_seconds: int) -> str:
    return LIMIT_EXCEEDED_MESSAGE.format(used_month_minutes=math.ceil(used_month_seconds / 60), available_minutes=math.ceil(available_seconds / 60))


START_MESSAGE = """
Привет! Я распознаю голосовые сообщения. Вы кидаете мне голосовое, я в ответ возвращаю его текстовую версию.

Есть ограничение на максимальную длину голосового — около 40-80 минут в зависимости от того, как именно оно записано. Ещё мне можно прислать голосовую заметку из встроенного приложения айфона.

Распознавание занимает от пары секунд до пары десятков секунд, в зависимости от длины аудио.

Ничего не записываю и не храню.

Каждый месяц тебе доступно {available_minutes} минут на распознавание.
"""


CHECK_AVAILABLE_MINUTES_MESSAGE = """
Использовано в этом месяце: {used_month_minutes}/{available_minutes} минут.
"""


ERROR_MESSAGE = """
Ошибочка: {error}
"""


LIMIT_EXCEEDED_MESSAGE = """
Ты достиг лимита на распознавание в этом месяце.

Использовано: {used_month_minutes}/{available_minutes} минут.
"""

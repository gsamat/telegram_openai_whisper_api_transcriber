from bot.models import Transcription, User, Payment
from config import settings
from django.utils import timezone
from datetime import timedelta


async def get_or_create_user(hashed_user_id: str) -> User:
    return await User.objects.aget_or_create(
        hashed_user_id=hashed_user_id,
        defaults=dict(left_free_seconds=settings.AVAILABLE_SECONDS),
    )


async def prepare_user_for_transcription(
    hashed_user_id: str, audio_duration: int
) -> tuple[User, str]:
    user, _ = await get_or_create_user(hashed_user_id)

    now = timezone.now()
    if user.last_free_reset_at < now - timedelta(days=30):
        user.left_free_seconds = settings.AVAILABLE_SECONDS
        user.last_free_reset_at = now
        user.warned_at = None
        await user.asave()

    if user.left_free_seconds + user.left_purchased_seconds < audio_duration:
        return user, "exceeded"
    elif (
        user.left_free_seconds + user.left_purchased_seconds
        < settings.LEFT_WARNING_SECONDS
    ):
        if user.warned_at:
            return user, "warned"
        else:
            user.warned_at = now
            await user.asave()
            return user, "show_warning"

    return user, "success"


async def process_user_transcription(
    user: User, audio_duration: int, transcription_time: float
) -> None:
    if audio_duration <= user.left_free_seconds:
        user.left_free_seconds -= audio_duration
    else:
        seconds_form_purchased = audio_duration - user.left_free_seconds
        user.left_free_seconds = 0
        user.left_purchased_seconds -= seconds_form_purchased
    await user.asave()


async def insert_transcription_log(
    user: User, audio_duration: int, transcription_time: float
) -> None:
    await Transcription.objects.acreate(
        user=user,
        audio_duration=audio_duration,
        transcription_time=transcription_time,
    )


async def make_payment(user: User, payment_id: str, total_amount: int) -> None:
    await Payment.objects.acreate(
        user=user,
        payment_id=payment_id,
        total_amount=total_amount,
    )
    user.left_purchased_seconds += total_amount * settings.CURRENCY_RATE_SECONDS
    await user.asave()

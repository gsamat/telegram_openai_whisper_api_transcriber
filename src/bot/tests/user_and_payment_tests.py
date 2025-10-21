import pytest
from bot.models import User, Transcription, Payment
from bot.services.db import get_or_create_user, insert_transcription_log, make_payment
from config import settings


pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]


async def test_get_or_create_user_creates_new_user():
    """
    Tests that a new user is created if one doesn't exist,
    with the default number of free seconds.
    """
    hashed_user_id = "new_user_to_create"
    assert await User.objects.filter(hashed_user_id=hashed_user_id).aexists() is False

    user, created = await get_or_create_user(hashed_user_id)

    assert created is True
    assert user.hashed_user_id == hashed_user_id
    assert user.left_free_seconds == settings.AVAILABLE_SECONDS
    assert await User.objects.filter(hashed_user_id=hashed_user_id).aexists() is True


async def test_get_or_create_user_retrieves_existing_user():
    """
    Tests that an existing user is retrieved correctly and a new one is not created.
    """
    existing_user = await User.objects.acreate(
        hashed_user_id="existing_user_to_find", left_free_seconds=500
    )

    user, created = await get_or_create_user(existing_user.hashed_user_id)

    assert created is False
    assert user.id == existing_user.id
    assert user.left_free_seconds == 500


async def test_insert_transcription_log():
    """
    Tests that a transcription log entry is created correctly.
    """
    user = await User.objects.acreate(hashed_user_id="user_for_transcription_log")
    audio_duration = 120
    transcription_time = 15.5

    await insert_transcription_log(user, audio_duration, transcription_time)

    log_entry = await Transcription.objects.aget(user=user)
    assert log_entry is not None
    assert log_entry.audio_duration == audio_duration
    assert log_entry.transcription_time == transcription_time


async def test_make_payment():
    """
    Tests that a payment is recorded and the user's purchased seconds are updated.
    """
    user = await User.objects.acreate(
        hashed_user_id="user_for_payment", left_purchased_seconds=100
    )
    payment_id = "test_payment_id_123"
    total_amount = 50  # This is the amount in the smallest currency unit

    # Assuming settings.CURRENCY_RATE_SECONDS is, for example, 10
    settings.CURRENCY_RATE_SECONDS = 10
    expected_seconds_added = total_amount * settings.CURRENCY_RATE_SECONDS

    await make_payment(user, payment_id, total_amount)

    # Verify the payment record was created
    payment = await Payment.objects.aget(payment_id=payment_id)
    assert payment is not None
    assert payment.user_id == user.id
    assert payment.total_amount == total_amount

    # Verify the user's purchased seconds were updated
    await user.arefresh_from_db()
    assert user.left_purchased_seconds == 100 + expected_seconds_added

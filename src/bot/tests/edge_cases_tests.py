import pytest

from datetime import timedelta
from django.utils import timezone
from bot.models import User
from bot.services.db import prepare_user_for_transcription, process_user_transcription
from config import settings


pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]


async def test_prepare_user_resets_free_seconds_after_30_days():
    """
    Tests that a user's free seconds are reset if more than 30 days have
    passed since the last reset.
    """
    thirty_one_days_ago = timezone.now() - timedelta(days=31)
    user = await User.objects.acreate(
        hashed_user_id="test_user_reset",
        left_free_seconds=50,  # Partially used
        last_free_reset_at=thirty_one_days_ago,
        warned_at=thirty_one_days_ago,
    )

    # Calling the function should trigger the reset
    await prepare_user_for_transcription(user.hashed_user_id, audio_duration=10)

    await user.arefresh_from_db()

    assert user.left_free_seconds == settings.AVAILABLE_SECONDS
    assert user.last_free_reset_at.date() == timezone.now().date()
    assert user.warned_at is None


async def test_prepare_user_does_not_reset_free_seconds_within_30_days():
    """
    Tests that a user's free seconds are NOT reset if it has been less
    than 30 days since the last reset.
    """
    ten_days_ago = timezone.now() - timedelta(days=10)
    user = await User.objects.acreate(
        hashed_user_id="test_user_no_reset",
        left_free_seconds=50,
        last_free_reset_at=ten_days_ago,
    )

    await prepare_user_for_transcription(user.hashed_user_id, audio_duration=10)

    await user.arefresh_from_db()

    # The free seconds should not have changed
    assert user.left_free_seconds == 50


async def test_process_transcription_exact_free_seconds_usage():
    """
    Tests the edge case where the audio duration is exactly equal to the
    user's remaining free seconds.
    """
    user = await User.objects.acreate(
        hashed_user_id="test_user_exact_usage",
        left_free_seconds=120,
        left_purchased_seconds=500,
    )
    audio_duration = 120

    await process_user_transcription(user, audio_duration, transcription_time=10.0)

    await user.arefresh_from_db()

    assert user.left_free_seconds == 0
    assert user.left_purchased_seconds == 500  # Purchased seconds should be untouched

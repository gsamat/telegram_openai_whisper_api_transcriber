import pytest
from bot.models import User
from bot.services.db import prepare_user_for_transcription, process_user_transcription
from config import settings
from django.utils import timezone
from datetime import timedelta

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]


async def test_prepare_user_for_transcription_success_free():
    """
    Tests the scenario where a user has enough free seconds for transcription.
    """
    user = await User.objects.acreate(
        hashed_user_id="test_user_free", left_free_seconds=100, left_purchased_seconds=0
    )
    user, status = await prepare_user_for_transcription(
        user.hashed_user_id, audio_duration=60
    )
    assert status == "success"


async def test_prepare_user_for_transcription_success_paid():
    """
    Tests the scenario where a user has no free seconds but enough purchased seconds.
    """
    user = await User.objects.acreate(
        hashed_user_id="test_user_paid", left_free_seconds=0, left_purchased_seconds=100
    )
    user, status = await prepare_user_for_transcription(
        user.hashed_user_id, audio_duration=60
    )
    assert status == "success"


async def test_prepare_user_for_transcription_success_mixed():
    """
    Tests the scenario where a user has a combination of free and purchased
    seconds that are sufficient for the transcription.
    """
    user = await User.objects.acreate(
        hashed_user_id="test_user_mixed",
        left_free_seconds=50,
        left_purchased_seconds=50,
    )
    user, status = await prepare_user_for_transcription(
        user.hashed_user_id, audio_duration=80
    )
    assert status == "success"


async def test_prepare_user_for_transcription_exceeded_limit():
    """
    Tests the scenario where a user does not have enough seconds for the transcription.
    """
    user = await User.objects.acreate(
        hashed_user_id="test_user_exceeded",
        left_free_seconds=30,
        left_purchased_seconds=20,
    )
    user, status = await prepare_user_for_transcription(
        user.hashed_user_id, audio_duration=60
    )
    assert status == "exceeded"


async def test_prepare_user_for_transcription_show_warning():
    """
    Tests that a warning is shown when the user's remaining seconds are below the threshold.
    """
    # Assuming settings.LEFT_WARNING_SECONDS is, for example, 300
    settings.LEFT_WARNING_SECONDS = 300
    user = await User.objects.acreate(
        hashed_user_id="test_user_warning",
        left_free_seconds=250,
        left_purchased_seconds=0,
    )
    user, status = await prepare_user_for_transcription(
        user.hashed_user_id, audio_duration=60
    )
    assert status == "show_warning"
    await user.arefresh_from_db()
    assert user.warned_at is not None


async def test_prepare_user_for_transcription_already_warned():
    """
    Tests that the status is 'warned' if a warning has already been issued recently.
    """
    settings.LEFT_WARNING_SECONDS = 300
    user = await User.objects.acreate(
        hashed_user_id="test_user_already_warned",
        left_free_seconds=250,
        left_purchased_seconds=0,
        warned_at=timezone.now() - timedelta(days=1),
    )
    user, status = await prepare_user_for_transcription(
        user.hashed_user_id, audio_duration=60
    )
    assert status == "warned"


async def test_process_user_transcription_purely_free():
    """
    Tests processing a transcription that only uses free seconds.
    """
    user = await User.objects.acreate(
        hashed_user_id="test_user_process_free",
        left_free_seconds=100,
        left_purchased_seconds=50,
    )
    await process_user_transcription(user, audio_duration=60, transcription_time=5.0)
    await user.arefresh_from_db()
    assert user.left_free_seconds == 40
    assert user.left_purchased_seconds == 50


async def test_process_user_transcription_mixed_free_and_paid():
    """
    Tests processing a transcription that uses up all free seconds and some purchased seconds.
    """
    user = await User.objects.acreate(
        hashed_user_id="test_user_process_mixed",
        left_free_seconds=50,
        left_purchased_seconds=100,
    )
    await process_user_transcription(user, audio_duration=80, transcription_time=7.0)
    await user.arefresh_from_db()
    assert user.left_free_seconds == 0
    assert user.left_purchased_seconds == 70  # 100 - (80 - 50)


async def test_process_user_transcription_purely_paid():
    """
    Tests processing a transcription that only uses purchased seconds.
    """
    user = await User.objects.acreate(
        hashed_user_id="test_user_process_paid",
        left_free_seconds=0,
        left_purchased_seconds=100,
    )
    await process_user_transcription(user, audio_duration=70, transcription_time=6.0)
    await user.arefresh_from_db()
    assert user.left_free_seconds == 0
    assert user.left_purchased_seconds == 30

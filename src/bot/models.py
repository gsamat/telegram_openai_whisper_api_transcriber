from django.db import models
from django.utils import timezone


class TimestampModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(TimestampModel):
    hashed_user_id = models.CharField(max_length=255, unique=True)
    left_free_seconds = models.IntegerField(default=0)
    left_purchased_seconds = models.IntegerField(default=0)
    last_free_reset_at = models.DateTimeField(default=timezone.now)
    warned_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Пользователь {self.hashed_user_id[:8]}..."


class Transcription(TimestampModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="transcriptions"
    )
    audio_duration = models.IntegerField()
    transcription_time = models.FloatField()

    def __str__(self):
        return f"Транскрипция #{self.id} от {self.user}"


class Payment(TimestampModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    payment_id = models.CharField(max_length=255)
    total_amount = models.IntegerField()

    def __str__(self):
        return f"Платеж {self.payment_id} на сумму {self.total_amount} от {self.user}"

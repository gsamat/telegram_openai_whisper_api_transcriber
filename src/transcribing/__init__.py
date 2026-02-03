"""Transcribing module - handles voice/audio transcription."""

from .handlers import register_handlers
from .whisper import transcribe_voice

__all__ = [
    "register_handlers",
    "transcribe_voice",
]

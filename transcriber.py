"""Business logic module for voice transcription.

This module contains the core transcription functionality and database
operations, separated from the Telegram bot handlers.
"""

import hashlib
import io
import time

import aiosqlite
import magic
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DATABASE_PATH = "transcriptions.db"
client = OpenAI()


async def log_transcription(
    hashed_user_id: str,
    audio_duration: int,
    transcription_time: float,
) -> None:
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transcriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hashed_user_id TEXT,
                audio_duration INTEGER,
                transcription_time REAL,
                created_at TEXT
            )
        """)
        await db.execute(
            "INSERT INTO transcriptions (hashed_user_id, audio_duration, transcription_time, created_at) VALUES (?, ?, ?, ?)",
            (hashed_user_id, audio_duration, transcription_time, current_time),
        )
        await db.commit()


def hash_user_id(user_id: int) -> str:
    return hashlib.sha256(str(user_id).encode()).hexdigest()


def detect_mime_type(file_data: io.BytesIO) -> str:
    file_data.seek(0)
    mime_type = magic.from_buffer(file_data.read(2048), mime=True)
    file_data.seek(0)
    return mime_type


def transcribe_audio(file_data: io.BytesIO, mime_type: str) -> tuple[str, float]:
    file = ("file", file_data.getvalue(), mime_type)
    start_time = time.time()
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=file,
        response_format="text",
    )
    transcription_time = time.time() - start_time
    return transcript, transcription_time

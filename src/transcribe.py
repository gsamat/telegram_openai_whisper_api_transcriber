import io
import os
from typing import TYPE_CHECKING

import magic
from openai import OpenAI
from telegram.ext import ContextTypes

if TYPE_CHECKING:
    from telegram import Audio, File, Voice


async def transcribe_voice(
    file: "Voice | Audio",
    context: ContextTypes.DEFAULT_TYPE,
) -> str:
    """Transcribe a voice message or audio file using OpenAI Whisper API.

    Args:
        file: Voice or Audio object from Telegram
        context: Bot context for downloading files

    Returns:
        Transcribed text

    Raises:
        Exception: If transcription fails
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        msg = "OPENAI_API_KEY environment variable is not set"
        raise RuntimeError(msg)

    client = OpenAI(api_key=openai_api_key)

    # Download file from Telegram
    file_handle: File = await context.bot.get_file(file.file_id)
    file_data = io.BytesIO()
    await file_handle.download_to_memory(file_data)
    file_data.seek(0)

    # Detect MIME type
    mime_type = magic.from_buffer(file_data.read(2048), mime=True)
    file_data.seek(0)

    # Prepare file tuple for OpenAI API
    file_tuple = ("file", file_data.getvalue(), mime_type)

    # Call Whisper API
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=file_tuple,
        response_format="text",
    )

    return transcript

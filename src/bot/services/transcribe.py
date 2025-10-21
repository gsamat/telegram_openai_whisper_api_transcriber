import io

from abc import ABC, abstractmethod

from config import settings


class TranscriptionService(ABC):
    @abstractmethod
    def transcribe(self, file_data: io.BytesIO, mime_type: str) -> str:
        pass


class OpenAIWhisperTS(TranscriptionService):
    def __init__(self):
        from openai import AsyncOpenAI

        if settings.OPENAI_API_KEY is None:
            raise ValueError("Для OpenAI необходимо установить OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def transcribe(self, file_data: io.BytesIO, mime_type: str) -> str:
        file_tuple = ("file", file_data.getvalue(), mime_type)
        transcript = await self.client.audio.transcriptions.create(
            model="whisper-1", file=file_tuple, response_format="text"
        )
        return transcript


class OpenAIGPT4oMiniTranscribeTS(TranscriptionService):
    def __init__(self):
        from openai import AsyncOpenAI

        if settings.OPENAI_API_KEY is None:
            raise ValueError("Для OpenAI необходимо установить OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def transcribe(self, file_data: io.BytesIO, mime_type: str) -> str:
        file_tuple = ("file", file_data.getvalue(), mime_type)
        transcript = await self.client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe", file=file_tuple, response_format="text"
        )
        return transcript


class ElevenLabsScribeV1TS(TranscriptionService):
    def __init__(self):
        from elevenlabs.client import AsyncElevenLabs

        api_key = settings.ELEVENLABS_API_KEY
        if api_key is None:
            raise ValueError("Для ElevenLabs необходимо установить ELEVENLABS_API_KEY")
        self.client = AsyncElevenLabs(api_key=api_key)

    async def transcribe(self, file_data: io.BytesIO, mime_type: str) -> str:
        response = await self.client.speech_to_text.convert(
            file=file_data, model_id="scribe_v1"
        )
        return response.text


class Gemini25FlashTranscribeTS(TranscriptionService):
    def __init__(self):
        from google import genai

        api_key = settings.GEMINI_API_KEY
        if api_key is None:
            raise ValueError("Для Gemini необходимо установить GEMINI_API_KEY")

        self.client = genai.Client()

    async def transcribe(self, file_data: io.BytesIO, mime_type: str) -> str:
        from google.genai.types import UploadFileConfig

        file = await self.client.aio.files.upload(
            file=file_data, config=UploadFileConfig(mime_type=mime_type)
        )
        prompt = "Generate a transcript of this audio file."
        response = await self.client.aio.models.generate_content(
            model="gemini-2.5-flash", contents=[prompt, file]
        )
        return response.text


def get_transcription_client(engine_name: str) -> TranscriptionService:
    if engine_name == "openai-whisper":
        print("Using OpenAI Whisper transcription engine.")
        return OpenAIWhisperTS()
    elif engine_name == "openai-gpt-4o-mini-transcribe":
        print("Using OpenAI GPT-4o Mini transcription engine.")
        return OpenAIGPT4oMiniTranscribeTS()
    elif engine_name == "elevenlabs-scribe_v1":
        print("Using ElevenLabs transcription engine.")
        return ElevenLabsScribeV1TS()
    elif engine_name == "gemini-2.5-flash":
        print("Using Gemini 2.5 Flash transcription engine.")
        return Gemini25FlashTranscribeTS()
    else:
        raise ValueError(f"Неизвестный движок транскрибации: {engine_name}")


transcription_client = get_transcription_client(settings.TRANSCRIPTION_ENGINE)

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.services.core_services.voice_service import VoiceService


@pytest.fixture
def mock_audio_io_service():
    mock_audio_io = AsyncMock()
    mock_audio_io.is_initialized.return_value = True
    mock_audio_io.start_recording.return_value = True
    mock_audio_io.stop_recording.return_value = True
    mock_audio_io.get_recording_status.return_value = {
        "recording": False,
        "duration": 0.0,
    }
    return mock_audio_io


@pytest.fixture
def mock_whisper_service():
    mock_whisper = AsyncMock()
    mock_whisper.transcribe_audio.return_value = {
        "text": "Hello world",
        "language": "en",
        "confidence": 0.95,
        "processing_time": 0.5,
    }
    return mock_whisper


@pytest.fixture
def mock_piper_tts_service():
    mock_piper = AsyncMock()
    mock_piper.generate_audio.return_value = "/tmp/test_audio.wav"
    return mock_piper


@pytest.fixture
def mock_chat_service():
    mock_chat = AsyncMock()
    mock_chat.process_message.return_value = MagicMock(
        response="Hi there!", emotion="happy"
    )
    return mock_chat


@pytest.fixture
def voice_service(
    mock_audio_io_service,
    mock_whisper_service,
    mock_piper_tts_service,
    mock_chat_service,
):
    with patch(
        "backend.chat_app.services.core_services.voice_service.get_audio_io_service",
        return_value=mock_audio_io_service,
    ), patch(
        "backend.chat_app.services.core_services.voice_service.get_whisper_service",
        return_value=mock_whisper_service,
    ), patch(
        "backend.chat_app.services.core_services.voice_service.get_piper_tts_service",
        return_value=mock_piper_tts_service,
    ), patch(
        "backend.chat_app.services.core_services.voice_service.get_chat_service",
        return_value=mock_chat_service,
    ):
        return VoiceService()


@pytest.mark.asyncio
async def test_start_recording(voice_service, mock_audio_io_service):
    result = await voice_service.start_recording("test_session")

    assert result["status"] == "recording_started"
    assert result["session_id"] == "test_session"
    mock_audio_io_service.start_recording.assert_called_once()


@pytest.mark.asyncio
async def test_stop_recording(voice_service, mock_audio_io_service):
    result = await voice_service.stop_recording("test_session")

    assert result["status"] == "recording_stopped"
    assert result["session_id"] == "test_session"
    mock_audio_io_service.stop_recording.assert_called_once()


@pytest.mark.asyncio
async def test_process_audio_file(
    voice_service, mock_whisper_service, mock_chat_service, mock_piper_tts_service
):
    audio_path = "/tmp/test_audio.wav"
    character = "hatsune_miku"

    result = await voice_service.process_audio_file(audio_path, character)

    assert result["transcription"]["text"] == "Hello world"
    assert result["chat_response"]["response"] == "Hi there!"
    assert result["audio_file"] == "/tmp/test_audio.wav"

    mock_whisper_service.transcribe_audio.assert_called_once_with(audio_path)
    mock_chat_service.process_message.assert_called_once()
    mock_piper_tts_service.generate_audio.assert_called_once()


@pytest.mark.asyncio
async def test_get_recording_status(voice_service, mock_audio_io_service):
    result = await voice_service.get_recording_status("test_session")

    assert "recording" in result
    assert "duration" in result
    mock_audio_io_service.get_recording_status.assert_called_once()


@pytest.mark.asyncio
async def test_transcribe_audio(voice_service, mock_whisper_service):
    audio_path = "/tmp/test.wav"

    result = await voice_service.transcribe_audio(audio_path)

    assert result["text"] == "Hello world"
    assert result["language"] == "en"
    assert result["confidence"] == 0.95
    mock_whisper_service.transcribe_audio.assert_called_once_with(audio_path)


@pytest.mark.asyncio
async def test_generate_speech(voice_service, mock_piper_tts_service):
    text = "Hello world"
    character = "hatsune_miku"

    result = await voice_service.generate_speech(text, character)

    assert result["audio_file"] == "/tmp/test_audio.wav"
    assert result["text"] == text
    assert result["character"] == character
    mock_piper_tts_service.generate_audio.assert_called_once_with(text, character)

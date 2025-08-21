import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import tempfile
import wave

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.services.stt_services.whisper_service import WhisperService


@pytest.fixture
def mock_whisper_model():
    mock_model = MagicMock()
    mock_result = MagicMock()
    mock_result.text = "Hello, this is a test transcription"
    mock_result.language = "en"
    mock_model.transcribe.return_value = mock_result
    return mock_model


@pytest.fixture
def whisper_service(mock_whisper_model):
    with patch("whisper.load_model", return_value=mock_whisper_model):
        service = WhisperService()
        service.model = mock_whisper_model
        return service


@pytest.fixture
def sample_audio_file():
    # Create a temporary WAV file for testing
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        # Create a simple mono 16-bit WAV file
        sample_rate = 16000
        duration = 1  # 1 second
        n_frames = sample_rate * duration

        with wave.open(temp_file.name, "wb") as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * n_frames)  # silence

        yield temp_file.name

        # Cleanup
        Path(temp_file.name).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_transcribe_audio_success(
    whisper_service, sample_audio_file, mock_whisper_model
):
    result = await whisper_service.transcribe_audio(sample_audio_file)

    assert result["text"] == "Hello, this is a test transcription"
    assert result["language"] == "en"
    assert "confidence" in result
    assert "processing_time" in result
    assert result["processing_time"] >= 0

    mock_whisper_model.transcribe.assert_called_once()


@pytest.mark.asyncio
async def test_transcribe_audio_file_not_found(whisper_service):
    with pytest.raises(FileNotFoundError):
        await whisper_service.transcribe_audio("/nonexistent/file.wav")


@pytest.mark.asyncio
async def test_transcribe_audio_with_options(
    whisper_service, sample_audio_file, mock_whisper_model
):
    options = {"language": "en", "task": "transcribe", "temperature": 0.0}

    result = await whisper_service.transcribe_audio(sample_audio_file, **options)

    assert result["text"] == "Hello, this is a test transcription"
    mock_whisper_model.transcribe.assert_called_once()

    # Verify options were passed to the transcribe call
    call_args = mock_whisper_model.transcribe.call_args
    assert call_args[0][0] == sample_audio_file
    assert call_args[1]["language"] == "en"
    assert call_args[1]["task"] == "transcribe"


@pytest.mark.asyncio
async def test_get_model_info(whisper_service):
    result = await whisper_service.get_model_info()

    assert "model_name" in result
    assert "initialized" in result
    assert result["initialized"] is True


@pytest.mark.asyncio
async def test_transcribe_empty_audio(whisper_service, mock_whisper_model):
    # Mock empty transcription result
    mock_result = MagicMock()
    mock_result.text = ""
    mock_result.language = "en"
    mock_whisper_model.transcribe.return_value = mock_result

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        # Create minimal empty WAV
        with wave.open(temp_file.name, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"")  # empty

        result = await whisper_service.transcribe_audio(temp_file.name)

        assert result["text"] == ""
        assert result["language"] == "en"

        Path(temp_file.name).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_transcribe_audio_processing_error(
    whisper_service, sample_audio_file, mock_whisper_model
):
    # Mock transcription error
    mock_whisper_model.transcribe.side_effect = Exception("Transcription failed")

    with pytest.raises(Exception, match="Transcription failed"):
        await whisper_service.transcribe_audio(sample_audio_file)

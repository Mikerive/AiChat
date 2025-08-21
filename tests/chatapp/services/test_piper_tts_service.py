import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import pytest
import tempfile
import json

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.services.tts_services.piper_tts_service import PiperTTSService


@pytest.fixture
def mock_piper_executable():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        yield mock_run


@pytest.fixture
def mock_model_files():
    model_data = {
        "audio": {"sample_rate": 22050},
        "dataset": "test_dataset",
        "language": {"code": "en"},
    }

    with patch("pathlib.Path.exists") as mock_exists, patch(
        "builtins.open", mock_open(read_data=json.dumps(model_data))
    ):
        mock_exists.return_value = True
        yield model_data


@pytest.fixture
def piper_service(mock_model_files):
    return PiperTTSService()


@pytest.mark.asyncio
async def test_generate_audio_success(piper_service, mock_piper_executable):
    text = "Hello world"
    character = "hatsune_miku"

    with patch("tempfile.NamedTemporaryFile") as mock_temp:
        mock_temp.return_value.__enter__.return_value.name = "/tmp/temp_audio.wav"

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            result = await piper_service.generate_audio(text, character)

            assert result.endswith(".wav")
            mock_piper_executable.assert_called_once()


@pytest.mark.asyncio
async def test_generate_audio_model_not_found(piper_service):
    text = "Hello world"
    character = "unknown_character"

    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError, match="Model not found"):
            await piper_service.generate_audio(text, character)


@pytest.mark.asyncio
async def test_generate_audio_empty_text(piper_service):
    result = await piper_service.generate_audio("", "hatsune_miku")

    # Should return placeholder for empty text
    assert result.endswith("placeholder.wav")


@pytest.mark.asyncio
async def test_generate_audio_piper_error(piper_service, mock_piper_executable):
    mock_piper_executable.return_value.returncode = 1
    mock_piper_executable.return_value.stderr = b"Piper error occurred"

    text = "Hello world"
    character = "hatsune_miku"

    with patch("tempfile.NamedTemporaryFile") as mock_temp:
        mock_temp.return_value.__enter__.return_value.name = "/tmp/temp_audio.wav"

        with pytest.raises(RuntimeError, match="Piper TTS failed"):
            await piper_service.generate_audio(text, character)


@pytest.mark.asyncio
async def test_get_available_models(piper_service):
    with patch("pathlib.Path.glob") as mock_glob:
        mock_glob.return_value = [
            Path("/models/en_US-amy-medium.onnx"),
            Path("/models/en_GB-alan-medium.onnx"),
        ]

        result = await piper_service.get_available_models()

        assert len(result) == 2
        assert "en_US-amy-medium" in result
        assert "en_GB-alan-medium" in result


@pytest.mark.asyncio
async def test_get_model_info(piper_service, mock_model_files):
    character = "hatsune_miku"

    result = await piper_service.get_model_info(character)

    assert result["sample_rate"] == 22050
    assert result["dataset"] == "test_dataset"
    assert result["language"] == "en"


@pytest.mark.asyncio
async def test_generate_audio_with_speed_control(piper_service, mock_piper_executable):
    text = "Hello world"
    character = "hatsune_miku"
    speed = 1.2

    with patch("tempfile.NamedTemporaryFile") as mock_temp:
        mock_temp.return_value.__enter__.return_value.name = "/tmp/temp_audio.wav"

        with patch("pathlib.Path.exists", return_value=True):
            result = await piper_service.generate_audio(text, character, speed=speed)

            assert result.endswith(".wav")
            # Verify speed parameter was passed to piper
            call_args = mock_piper_executable.call_args[0][0]
            assert "--length-scale" in call_args
            assert str(1 / speed) in call_args


@pytest.mark.asyncio
async def test_generate_placeholder_audio(piper_service):
    text = "Test text"
    character = "hatsune_miku"

    result = await piper_service._generate_placeholder_audio(text, character)

    assert result.endswith("_placeholder.wav")
    assert character in result or "placeholder" in result


@pytest.mark.asyncio
async def test_cleanup_old_audio_files(piper_service):
    with patch("pathlib.Path.glob") as mock_glob, patch(
        "pathlib.Path.unlink"
    ) as mock_unlink, patch("pathlib.Path.stat") as mock_stat:

        # Mock old files
        old_file = MagicMock()
        old_file.stat.return_value.st_mtime = 1000000  # Very old timestamp
        mock_glob.return_value = [old_file]

        await piper_service.cleanup_old_files(max_age_hours=1)

        old_file.unlink.assert_called_once()

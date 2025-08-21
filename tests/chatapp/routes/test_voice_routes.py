import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
import tempfile
import wave

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.routes.voice import router
from fastapi import FastAPI


@pytest.fixture
def mock_voice_service():
    mock_service = AsyncMock()
    mock_service.start_recording.return_value = {
        "status": "recording_started",
        "session_id": "test_session",
    }
    mock_service.stop_recording.return_value = {
        "status": "recording_stopped",
        "session_id": "test_session",
    }
    mock_service.get_recording_status.return_value = {
        "recording": False,
        "duration": 0.0,
    }
    mock_service.process_audio_file.return_value = {
        "transcription": {"text": "Hello world", "language": "en", "confidence": 0.95},
        "chat_response": {"response": "Hi there!", "emotion": "happy"},
        "audio_file": "/tmp/response.wav",
    }
    mock_service.transcribe_audio.return_value = {
        "text": "Hello world",
        "language": "en",
        "confidence": 0.95,
        "processing_time": 0.5,
    }
    mock_service.generate_speech.return_value = {
        "audio_file": "/tmp/speech.wav",
        "text": "Hello",
        "character": "hatsune_miku",
    }
    return mock_service


@pytest.fixture
def mock_db_ops():
    mock_db = AsyncMock()
    mock_db.list_voice_models.return_value = [
        MagicMock(id=1, name="hatsune_miku", model_path="/models/miku.onnx")
    ]
    mock_db.list_training_data.return_value = [
        MagicMock(id=1, filename="sample.wav", transcript="Hello", duration=1.0)
    ]
    mock_db.create_training_data.return_value = MagicMock(
        id=2, filename="new_sample.wav"
    )
    return mock_db


@pytest.fixture
def app_with_mocks(mock_voice_service, mock_db_ops):
    app = FastAPI()

    with patch(
        "backend.chat_app.routes.voice.get_voice_service_dep",
        return_value=mock_voice_service,
    ), patch("backend.chat_app.routes.voice.db_ops", mock_db_ops):

        app.include_router(router, prefix="/api/voice")
        yield app


def test_start_recording(app_with_mocks, mock_voice_service):
    client = TestClient(app_with_mocks)

    payload = {"session_id": "test_session"}
    response = client.post("/api/voice/record/start", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recording_started"
    assert data["session_id"] == "test_session"
    mock_voice_service.start_recording.assert_called_once_with("test_session")


def test_stop_recording(app_with_mocks, mock_voice_service):
    client = TestClient(app_with_mocks)

    payload = {"session_id": "test_session"}
    response = client.post("/api/voice/record/stop", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recording_stopped"
    mock_voice_service.stop_recording.assert_called_once_with("test_session")


def test_get_recording_status(app_with_mocks, mock_voice_service):
    client = TestClient(app_with_mocks)

    response = client.get("/api/voice/record/status/test_session")

    assert response.status_code == 200
    data = response.json()
    assert "recording" in data
    assert "duration" in data
    mock_voice_service.get_recording_status.assert_called_once_with("test_session")


def test_process_audio_upload(app_with_mocks, mock_voice_service):
    client = TestClient(app_with_mocks)

    # Create a temporary WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        with wave.open(temp_file.name, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 16000)

        with open(temp_file.name, "rb") as audio_file:
            files = {"file": ("test.wav", audio_file, "audio/wav")}
            data = {"character": "hatsune_miku"}
            response = client.post("/api/voice/process", files=files, data=data)

        Path(temp_file.name).unlink(missing_ok=True)

    assert response.status_code == 200
    result = response.json()
    assert "transcription" in result
    assert "chat_response" in result
    assert "audio_file" in result
    mock_voice_service.process_audio_file.assert_called_once()


def test_transcribe_audio(app_with_mocks, mock_voice_service):
    client = TestClient(app_with_mocks)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        with wave.open(temp_file.name, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 16000)

        with open(temp_file.name, "rb") as audio_file:
            response = client.post(
                "/api/voice/transcribe",
                files={"file": ("test.wav", audio_file, "audio/wav")},
            )

        Path(temp_file.name).unlink(missing_ok=True)

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "Hello world"
    assert data["language"] == "en"
    mock_voice_service.transcribe_audio.assert_called_once()


def test_generate_speech(app_with_mocks, mock_voice_service):
    client = TestClient(app_with_mocks)

    payload = {"text": "Hello", "character": "hatsune_miku"}
    response = client.post("/api/voice/speak", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["audio_file"] == "/tmp/speech.wav"
    assert data["text"] == "Hello"
    assert data["character"] == "hatsune_miku"
    mock_voice_service.generate_speech.assert_called_once_with("Hello", "hatsune_miku")


def test_list_voice_models(app_with_mocks, mock_db_ops):
    client = TestClient(app_with_mocks)

    response = client.get("/api/voice/models")

    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], list)
    assert len(data["models"]) == 1
    mock_db_ops.list_voice_models.assert_called_once()


def test_list_training_data(app_with_mocks, mock_db_ops):
    client = TestClient(app_with_mocks)

    response = client.get("/api/voice/training-data")

    assert response.status_code == 200
    data = response.json()
    assert "training_data" in data
    assert isinstance(data["training_data"], list)
    mock_db_ops.list_training_data.assert_called_once()


def test_upload_training_data(app_with_mocks, mock_db_ops):
    client = TestClient(app_with_mocks)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        with wave.open(temp_file.name, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 16000)

        with open(temp_file.name, "rb") as audio_file:
            files = {"file": ("training.wav", audio_file, "audio/wav")}
            data = {
                "transcript": "Hello world",
                "speaker": "hatsune_miku",
                "quality": "high",
            }
            response = client.post("/api/voice/training-data", files=files, data=data)

        Path(temp_file.name).unlink(missing_ok=True)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "uploaded"
    assert "training_data_id" in result
    mock_db_ops.create_training_data.assert_called_once()


def test_upload_training_data_missing_file(app_with_mocks):
    client = TestClient(app_with_mocks)

    data = {"transcript": "Hello world"}
    response = client.post("/api/voice/training-data", data=data)

    assert response.status_code == 422  # No file provided


def test_process_audio_missing_file(app_with_mocks):
    client = TestClient(app_with_mocks)

    data = {"character": "hatsune_miku"}
    response = client.post("/api/voice/process", data=data)

    assert response.status_code == 422  # No file provided


def test_generate_speech_missing_text(app_with_mocks):
    client = TestClient(app_with_mocks)

    payload = {"character": "hatsune_miku"}
    response = client.post("/api/voice/speak", json=payload)

    assert response.status_code == 422  # Missing text field

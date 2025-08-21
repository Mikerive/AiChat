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

from backend.chat_app.routes.chat import router
from fastapi import FastAPI


@pytest.fixture
def mock_chat_service():
    mock_service = AsyncMock()
    mock_service.process_message.return_value = MagicMock(
        response="Hello! How can I help you?", emotion="happy", model_used="test-model"
    )
    mock_service.switch_character.return_value = True
    mock_service.generate_tts.return_value = "/tmp/test_audio.wav"
    mock_service.get_current_character.return_value = {"id": 1, "name": "hatsune_miku"}
    return mock_service


@pytest.fixture
def mock_whisper_service():
    mock_service = AsyncMock()
    mock_service.transcribe_audio.return_value = {
        "text": "Hello world",
        "language": "en",
        "confidence": 0.95,
        "processing_time": 0.5,
    }
    return mock_service


@pytest.fixture
def mock_db_ops():
    mock_db = AsyncMock()
    mock_db.list_characters.return_value = [
        MagicMock(
            id=1,
            name="hatsune_miku",
            profile="A virtual singer",
            personality="cheerful",
            avatar_url=None,
        )
    ]
    mock_db.get_character.return_value = MagicMock(
        id=1,
        name="hatsune_miku",
        profile="A virtual singer",
        personality="cheerful",
        avatar_url=None,
    )
    mock_db.get_chat_logs.return_value = [
        MagicMock(
            id=1,
            character_id=1,
            user_message="Hi",
            character_response="Hello!",
            timestamp="2024-01-01T00:00:00",
            emotion="happy",
            metadata={},
        )
    ]
    return mock_db


@pytest.fixture
def app_with_mocks(mock_chat_service, mock_whisper_service, mock_db_ops):
    app = FastAPI()

    with patch(
        "backend.chat_app.routes.chat.get_chat_service_dep",
        return_value=mock_chat_service,
    ), patch(
        "backend.chat_app.routes.chat.get_whisper_service_dep",
        return_value=mock_whisper_service,
    ), patch(
        "backend.chat_app.routes.chat.db_ops", mock_db_ops
    ), patch(
        "backend.chat_app.routes.chat.emit_chat_response", new_callable=AsyncMock
    ):

        app.include_router(router, prefix="/api/chat")
        yield app


def test_list_characters(app_with_mocks, mock_db_ops):
    client = TestClient(app_with_mocks)

    response = client.get("/api/chat/characters")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "hatsune_miku"
    mock_db_ops.list_characters.assert_called_once()


def test_get_character(app_with_mocks, mock_db_ops):
    client = TestClient(app_with_mocks)

    response = client.get("/api/chat/characters/1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "hatsune_miku"
    mock_db_ops.get_character.assert_called_once_with(1)


def test_get_character_not_found(app_with_mocks, mock_db_ops):
    mock_db_ops.get_character.return_value = None
    client = TestClient(app_with_mocks)

    response = client.get("/api/chat/characters/999")

    assert response.status_code == 404


def test_chat_endpoint(app_with_mocks, mock_chat_service):
    client = TestClient(app_with_mocks)

    payload = {"text": "Hello", "character": "hatsune_miku"}
    response = client.post("/api/chat/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["user_input"] == "Hello"
    assert data["response"] == "Hello! How can I help you?"
    assert data["emotion"] == "happy"
    mock_chat_service.process_message.assert_called_once()


def test_chat_endpoint_missing_text(app_with_mocks):
    client = TestClient(app_with_mocks)

    payload = {"character": "hatsune_miku"}
    response = client.post("/api/chat/chat", json=payload)

    assert response.status_code == 422  # Validation error


def test_switch_character(app_with_mocks, mock_chat_service):
    client = TestClient(app_with_mocks)

    payload = {"character": "hatsune_miku"}
    response = client.post("/api/chat/switch_character", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "switched"
    assert data["character"] == "hatsune_miku"
    mock_chat_service.switch_character.assert_called_once()


def test_switch_character_failed(app_with_mocks, mock_chat_service):
    mock_chat_service.switch_character.return_value = False
    client = TestClient(app_with_mocks)

    payload = {"character": "unknown"}
    response = client.post("/api/chat/switch_character", json=payload)

    assert response.status_code == 400


def test_tts_endpoint(app_with_mocks, mock_chat_service):
    client = TestClient(app_with_mocks)

    payload = {"text": "Hello world", "character": "hatsune_miku"}
    response = client.post("/api/chat/tts", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["audio_format"] == "wav"
    assert data["audio_file"] == "/tmp/test_audio.wav"
    mock_chat_service.generate_tts.assert_called_once()


def test_stt_endpoint(app_with_mocks, mock_whisper_service):
    client = TestClient(app_with_mocks)

    # Create a temporary WAV file for testing
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        with wave.open(temp_file.name, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 16000)  # 1 second of silence

        with open(temp_file.name, "rb") as audio_file:
            response = client.post(
                "/api/chat/stt", files={"file": ("test.wav", audio_file, "audio/wav")}
            )

        Path(temp_file.name).unlink(missing_ok=True)

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "Hello world"
    assert data["language"] == "en"
    mock_whisper_service.transcribe_audio.assert_called_once()


def test_stt_endpoint_no_file(app_with_mocks):
    client = TestClient(app_with_mocks)

    response = client.post("/api/chat/stt")

    assert response.status_code == 422  # No file provided


def test_get_chat_history(app_with_mocks, mock_db_ops):
    client = TestClient(app_with_mocks)

    response = client.get("/api/chat/chat/history")

    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)
    mock_db_ops.get_chat_logs.assert_called_once()


def test_get_chat_history_with_character(app_with_mocks, mock_db_ops):
    client = TestClient(app_with_mocks)

    response = client.get("/api/chat/chat/history?character_id=1")

    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    mock_db_ops.get_chat_logs.assert_called_once_with(character_id=1, limit=100)


def test_get_status(app_with_mocks, mock_chat_service):
    client = TestClient(app_with_mocks)

    response = client.get("/api/chat/status")

    assert response.status_code == 200
    data = response.json()
    assert data["backend"] == "running"
    assert "current_character" in data
    mock_chat_service.get_current_character.assert_called_once()

"""
Route tests using the actual test database.
These tests verify that the API routes work correctly with real database data.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.routes.chat import router as chat_router
from backend.chat_app.routes.voice import router as voice_router


@pytest.fixture
def mock_services():
    """Mock the services that routes depend on"""
    mock_chat_service = AsyncMock()
    mock_chat_service.process_message.return_value = MagicMock(
        response="Hello! How can I help you?", emotion="happy", model_used="test-model"
    )
    mock_chat_service.switch_character.return_value = True
    mock_chat_service.generate_tts.return_value = "/tmp/test_audio.wav"
    mock_chat_service.get_current_character.return_value = {
        "id": 1,
        "name": "hatsune_miku",
    }

    mock_whisper_service = AsyncMock()
    mock_whisper_service.transcribe_audio.return_value = {
        "text": "Hello world",
        "language": "en",
        "confidence": 0.95,
        "processing_time": 0.5,
    }

    mock_voice_service = AsyncMock()
    mock_voice_service.transcribe_audio.return_value = {
        "text": "Hello world",
        "language": "en",
        "confidence": 0.95,
        "processing_time": 0.5,
    }

    return mock_chat_service, mock_whisper_service, mock_voice_service


@pytest.fixture
def app_with_test_db(mock_services, test_db_operations):
    """Create FastAPI app with test database and mocked services"""
    mock_chat_service, mock_whisper_service, mock_voice_service = mock_services

    app = FastAPI()

    with patch(
        "backend.chat_app.routes.chat.get_chat_service_dep",
        return_value=mock_chat_service,
    ), patch(
        "backend.chat_app.routes.chat.get_whisper_service_dep",
        return_value=mock_whisper_service,
    ), patch(
        "backend.chat_app.routes.chat.db_ops", test_db_operations
    ), patch(
        "backend.chat_app.routes.chat.emit_chat_response", new_callable=AsyncMock
    ), patch(
        "backend.chat_app.routes.voice.get_voice_service_dep",
        return_value=mock_voice_service,
    ), patch(
        "backend.chat_app.routes.voice.db_ops", test_db_operations
    ):

        app.include_router(chat_router, prefix="/api/chat")
        app.include_router(voice_router, prefix="/api/voice")
        yield app


def test_list_characters_with_test_db(app_with_test_db):
    """Test listing characters using real test database data"""
    client = TestClient(app_with_test_db)

    response = client.get("/api/chat/characters")

    assert response.status_code == 200
    characters = response.json()
    assert isinstance(characters, list)
    assert len(characters) >= 3  # We have 3 sample characters

    # Check that we have the expected characters
    character_names = [c["name"] for c in characters]
    assert "hatsune_miku" in character_names
    assert "kagamine_rin" in character_names
    assert "megurine_luka" in character_names

    # Check character details
    miku = next(c for c in characters if c["name"] == "hatsune_miku")
    assert miku["id"] == 1
    assert "virtual singer" in miku["profile"].lower()
    assert "cheerful" in miku["personality"].lower()


def test_get_character_with_test_db(app_with_test_db):
    """Test getting specific character using real test database data"""
    client = TestClient(app_with_test_db)

    # Test getting Miku (ID 1)
    response = client.get("/api/chat/characters/1")

    assert response.status_code == 200
    character = response.json()
    assert character["id"] == 1
    assert character["name"] == "hatsune_miku"
    assert "virtual singer" in character["profile"].lower()

    # Test getting Rin (ID 2)
    response = client.get("/api/chat/characters/2")

    assert response.status_code == 200
    character = response.json()
    assert character["id"] == 2
    assert character["name"] == "kagamine_rin"

    # Test getting non-existent character
    response = client.get("/api/chat/characters/999")
    assert response.status_code == 404


def test_chat_history_with_test_db(app_with_test_db):
    """Test getting chat history using real test database data"""
    client = TestClient(app_with_test_db)

    # Test getting all chat history
    response = client.get("/api/chat/chat/history")

    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)
    assert len(data["history"]) >= 4  # We have 4 sample chat logs

    # Check chat log structure
    first_log = data["history"][0]
    assert "id" in first_log
    assert "character_id" in first_log
    assert "user_message" in first_log
    assert "character_response" in first_log
    assert "timestamp" in first_log


def test_chat_history_by_character_with_test_db(app_with_test_db):
    """Test getting chat history for specific character using real test database data"""
    client = TestClient(app_with_test_db)

    # Test getting chat history for Miku (character_id=1)
    response = client.get("/api/chat/chat/history?character_id=1")

    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)

    # All logs should be for character 1 (Miku)
    for log in data["history"]:
        assert log["character_id"] == 1

    # Should have at least 2 Miku logs based on sample data
    assert len(data["history"]) >= 2


def test_voice_models_with_test_db(app_with_test_db):
    """Test listing voice models using real test database data"""
    client = TestClient(app_with_test_db)

    response = client.get("/api/voice/models")

    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], list)
    assert len(data["models"]) >= 2  # We have 2 sample voice models

    # Check that we have the expected models
    model_names = [m["name"] for m in data["models"]]
    assert "hatsune_miku_v1" in model_names
    assert "kagamine_rin_v1" in model_names

    # Check model details
    miku_model = next(m for m in data["models"] if m["name"] == "hatsune_miku_v1")
    assert miku_model["character_id"] == 1
    assert miku_model["status"] == "trained"


def test_training_data_with_test_db(app_with_test_db):
    """Test listing training data using real test database data"""
    client = TestClient(app_with_test_db)

    response = client.get("/api/voice/training-data")

    assert response.status_code == 200
    data = response.json()
    assert "training_data" in data
    assert isinstance(data["training_data"], list)
    assert len(data["training_data"]) >= 3  # We have 3 sample training data entries

    # Check that we have the expected files
    filenames = [td["filename"] for td in data["training_data"]]
    assert "miku_sample_01.wav" in filenames
    assert "miku_sample_02.wav" in filenames
    assert "rin_sample_01.wav" in filenames

    # Check training data details
    miku_sample = next(
        td for td in data["training_data"] if td["filename"] == "miku_sample_01.wav"
    )
    assert miku_sample["speaker"] == "hatsune_miku"
    assert miku_sample["transcript"] == "Hello everyone! I'm Hatsune Miku!"
    assert miku_sample["duration"] == 2.5


def test_chat_endpoint_with_test_db_character(app_with_test_db, mock_services):
    """Test chat endpoint works with characters from test database"""
    client = TestClient(app_with_test_db)
    mock_chat_service, _, _ = mock_services

    # Test chatting with Miku (exists in test DB)
    payload = {"text": "Hello Miku!", "character": "hatsune_miku"}
    response = client.post("/api/chat/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["user_input"] == "Hello Miku!"
    assert data["response"] == "Hello! How can I help you?"

    # Verify the service was called with the right character
    mock_chat_service.process_message.assert_called_once()
    call_args = mock_chat_service.process_message.call_args
    assert call_args[0][0] == "Hello Miku!"  # text
    assert call_args[0][2] == "hatsune_miku"  # character name


def test_character_switch_with_test_db(app_with_test_db, mock_services):
    """Test character switching with characters from test database"""
    client = TestClient(app_with_test_db)
    mock_chat_service, _, _ = mock_services

    # Test switching to Rin (exists in test DB)
    payload = {"character": "kagamine_rin"}
    response = client.post("/api/chat/switch_character", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "switched"
    assert data["character"] == "kagamine_rin"

    # Verify the service was called with the right character
    mock_chat_service.switch_character.assert_called_once()
    call_args = mock_chat_service.switch_character.call_args
    assert call_args[0][1] == "kagamine_rin"  # character name

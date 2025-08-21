import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import datetime

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.services.core_services.chat_service import ChatService


@pytest.fixture
def mock_db_ops():
    mock_db = AsyncMock()
    mock_db.get_character_by_name.return_value = MagicMock(
        id=1, name="hatsune_miku", personality="cheerful", profile="A virtual singer"
    )
    mock_db.create_chat_log.return_value = MagicMock(id=1)
    return mock_db


@pytest.fixture
def mock_openrouter():
    mock_openrouter = AsyncMock()
    mock_openrouter.generate_response.return_value = MagicMock(
        response="Hello! How can I help you?", emotion="happy", model_used="test-model"
    )
    return mock_openrouter


@pytest.fixture
def mock_piper_tts():
    mock_piper = AsyncMock()
    mock_piper.generate_audio.return_value = "/tmp/test_audio.wav"
    return mock_piper


@pytest.fixture
def chat_service(mock_db_ops, mock_openrouter, mock_piper_tts):
    with patch(
        "backend.chat_app.services.core_services.chat_service.db_ops", mock_db_ops
    ), patch(
        "backend.chat_app.services.core_services.chat_service.get_openrouter_service",
        return_value=mock_openrouter,
    ), patch(
        "backend.chat_app.services.core_services.chat_service.get_piper_tts_service",
        return_value=mock_piper_tts,
    ):
        return ChatService()


@pytest.mark.asyncio
async def test_process_message_success(chat_service, mock_db_ops, mock_openrouter):
    result = await chat_service.process_message("Hello", 1, "hatsune_miku")

    assert result.response == "Hello! How can I help you?"
    assert result.emotion == "happy"
    assert result.model_used == "test-model"

    mock_openrouter.generate_response.assert_called_once()
    mock_db_ops.create_chat_log.assert_called_once()


@pytest.mark.asyncio
async def test_process_message_character_not_found(
    chat_service, mock_db_ops, mock_openrouter
):
    mock_db_ops.get_character_by_name.return_value = None

    with pytest.raises(ValueError, match="Character .* not found"):
        await chat_service.process_message("Hello", 1, "unknown_character")


@pytest.mark.asyncio
async def test_switch_character_success(chat_service, mock_db_ops):
    result = await chat_service.switch_character(1, "hatsune_miku")

    assert result is True
    assert chat_service.current_character == "hatsune_miku"
    mock_db_ops.get_character_by_name.assert_called_once_with("hatsune_miku")


@pytest.mark.asyncio
async def test_switch_character_not_found(chat_service, mock_db_ops):
    mock_db_ops.get_character_by_name.return_value = None

    result = await chat_service.switch_character(1, "unknown")

    assert result is False


@pytest.mark.asyncio
async def test_generate_tts_success(chat_service, mock_piper_tts):
    result = await chat_service.generate_tts("Hello world", 1, "hatsune_miku")

    assert result == "/tmp/test_audio.wav"
    mock_piper_tts.generate_audio.assert_called_once_with("Hello world", "hatsune_miku")


@pytest.mark.asyncio
async def test_get_current_character(chat_service, mock_db_ops):
    chat_service.current_character = "hatsune_miku"

    result = await chat_service.get_current_character()

    assert result["name"] == "hatsune_miku"
    mock_db_ops.get_character_by_name.assert_called_once_with("hatsune_miku")


@pytest.mark.asyncio
async def test_get_current_character_none(chat_service):
    chat_service.current_character = None

    result = await chat_service.get_current_character()

    assert result is None

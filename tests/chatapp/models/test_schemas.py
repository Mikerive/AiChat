import sys
from pathlib import Path
import pytest
from datetime import datetime
from pydantic import ValidationError

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.models.schemas import (
    ChatMessage,
    ChatResponse,
    TTSRequest,
    TTSResponse,
    STTResponse,
    Character,
    SwitchCharacterRequest,
    VoiceProcessingRequest,
    VoiceProcessingResponse,
    WebhookRequest,
    SystemStatus,
)


class TestChatMessage:
    def test_valid_chat_message(self):
        message = ChatMessage(text="Hello", character="hatsune_miku")
        assert message.text == "Hello"
        assert message.character == "hatsune_miku"

    def test_chat_message_missing_text(self):
        with pytest.raises(ValidationError):
            ChatMessage(character="hatsune_miku")

    def test_chat_message_missing_character(self):
        with pytest.raises(ValidationError):
            ChatMessage(text="Hello")

    def test_chat_message_empty_text(self):
        with pytest.raises(ValidationError):
            ChatMessage(text="", character="hatsune_miku")

    def test_chat_message_whitespace_text(self):
        with pytest.raises(ValidationError):
            ChatMessage(text="   ", character="hatsune_miku")


class TestChatResponse:
    def test_valid_chat_response(self):
        response = ChatResponse(
            user_input="Hello",
            response="Hi there!",
            character="hatsune_miku",
            emotion="happy",
            model_used="gpt-4",
            timestamp=datetime.now(),
        )
        assert response.user_input == "Hello"
        assert response.response == "Hi there!"
        assert response.emotion == "happy"

    def test_chat_response_optional_fields(self):
        response = ChatResponse(user_input="Hello", response="Hi!", character="miku")
        assert response.emotion is None
        assert response.model_used is None
        assert response.timestamp is not None  # Should be auto-generated


class TestTTSRequest:
    def test_valid_tts_request(self):
        request = TTSRequest(text="Hello world", character="hatsune_miku")
        assert request.text == "Hello world"
        assert request.character == "hatsune_miku"
        assert request.speed == 1.0  # Default value

    def test_tts_request_with_speed(self):
        request = TTSRequest(text="Hello", character="miku", speed=1.2)
        assert request.speed == 1.2

    def test_tts_request_invalid_speed(self):
        with pytest.raises(ValidationError):
            TTSRequest(text="Hello", character="miku", speed=0.0)

        with pytest.raises(ValidationError):
            TTSRequest(text="Hello", character="miku", speed=3.0)


class TestTTSResponse:
    def test_valid_tts_response(self):
        response = TTSResponse(
            audio_file="/tmp/audio.wav",
            audio_format="wav",
            character="hatsune_miku",
            text="Hello world",
        )
        assert response.audio_file == "/tmp/audio.wav"
        assert response.audio_format == "wav"
        assert response.duration is None  # Optional field


class TestSTTResponse:
    def test_valid_stt_response(self):
        response = STTResponse(
            text="Hello world", language="en", confidence=0.95, processing_time=0.5
        )
        assert response.text == "Hello world"
        assert response.language == "en"
        assert response.confidence == 0.95

    def test_stt_response_confidence_bounds(self):
        with pytest.raises(ValidationError):
            STTResponse(text="Hello", language="en", confidence=-0.1)

        with pytest.raises(ValidationError):
            STTResponse(text="Hello", language="en", confidence=1.1)


class TestCharacter:
    def test_valid_character(self):
        character = Character(
            id=1,
            name="hatsune_miku",
            profile="A virtual singer",
            personality="cheerful and energetic",
        )
        assert character.id == 1
        assert character.name == "hatsune_miku"
        assert character.avatar_url is None  # Optional field

    def test_character_with_avatar(self):
        character = Character(
            id=2,
            name="kagamine_rin",
            profile="Twin vocalist",
            personality="energetic",
            avatar_url="https://example.com/rin.jpg",
        )
        assert character.avatar_url == "https://example.com/rin.jpg"


class TestSwitchCharacterRequest:
    def test_valid_switch_request(self):
        request = SwitchCharacterRequest(character="hatsune_miku")
        assert request.character == "hatsune_miku"

    def test_switch_request_empty_character(self):
        with pytest.raises(ValidationError):
            SwitchCharacterRequest(character="")


class TestVoiceProcessingRequest:
    def test_valid_voice_processing_request(self):
        request = VoiceProcessingRequest(character="hatsune_miku")
        assert request.character == "hatsune_miku"
        assert request.session_id is None  # Optional field

    def test_voice_processing_with_session(self):
        request = VoiceProcessingRequest(character="miku", session_id="session_123")
        assert request.session_id == "session_123"


class TestVoiceProcessingResponse:
    def test_valid_voice_processing_response(self):
        response = VoiceProcessingResponse(
            transcription={"text": "Hello", "language": "en", "confidence": 0.9},
            chat_response={"response": "Hi there!", "emotion": "happy"},
            audio_file="/tmp/response.wav",
        )
        assert response.transcription["text"] == "Hello"
        assert response.chat_response["response"] == "Hi there!"
        assert response.audio_file == "/tmp/response.wav"


class TestWebhookRequest:
    def test_valid_webhook_request(self):
        request = WebhookRequest(url="https://example.com/webhook")
        assert request.url == "https://example.com/webhook"

    def test_webhook_request_invalid_url(self):
        with pytest.raises(ValidationError):
            WebhookRequest(url="not-a-url")

        with pytest.raises(ValidationError):
            WebhookRequest(url="ftp://example.com")  # Only http/https allowed


class TestSystemStatus:
    def test_valid_system_status(self):
        status = SystemStatus(
            status="running",
            uptime=3600.5,
            memory_usage={"used": 1000, "total": 2000},
            services={"chat": "running", "tts": "running"},
        )
        assert status.status == "running"
        assert status.uptime == 3600.5
        assert status.memory_usage["used"] == 1000
        assert status.services["chat"] == "running"

    def test_system_status_invalid_status(self):
        with pytest.raises(ValidationError):
            SystemStatus(
                status="invalid_status", uptime=100, memory_usage={}, services={}
            )

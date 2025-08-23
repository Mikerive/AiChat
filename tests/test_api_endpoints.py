"""
Comprehensive test suite for FastAPI endpoints
Tests all API routes with proper Pydantic model validation
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Import the FastAPI app
from aichat.backend.main import create_app
from aichat.models.schemas import (
    Character,
    ChatMessage,
    CharacterResponse,
    CharacterSwitchResponse,
    TTSRequest,
    TTSResponse,
    STTResponse,
    ChatHistoryResponse,
    SystemStatusResponse,
    AudioDevicesResponse,
    AudioDeviceInfo,
    ChatterboxStatusResponse,
    IntensityStreamingResponse,
)


@pytest.fixture
def app():
    """Create FastAPI test app"""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_character():
    """Mock character data"""
    return {
        "id": 1,
        "name": "test_character",
        "profile": "A test character for unit testing",
        "personality": "friendly and helpful",
        "avatar_url": "https://example.com/avatar.png"
    }


@pytest.fixture
def mock_chat_service():
    """Mock chat service"""
    mock = AsyncMock()
    mock.process_message.return_value = Mock(
        response="Hello! How can I help you?",
        emotion="happy",
        model_used="test_model"
    )
    mock.generate_tts.return_value = Path("test_audio.wav")
    mock.switch_character.return_value = True
    mock.get_current_character.return_value = {
        "id": 1,
        "name": "test_character"
    }
    return mock


@pytest.fixture
def mock_whisper_service():
    """Mock whisper service"""
    mock = AsyncMock()
    mock.transcribe_audio.return_value = {
        "text": "Hello, this is a test transcription",
        "language": "en",
        "confidence": 0.95,
        "processing_time": 1.2
    }
    return mock


@pytest.fixture
def mock_audio_io_service():
    """Mock audio IO service"""
    mock = AsyncMock()
    mock.get_input_devices.return_value = [
        Mock(id=0, name="Test Input", channels=2, sample_rate=44100, is_default=True)
    ]
    mock.get_output_devices.return_value = [
        Mock(id=0, name="Test Output", channels=2, sample_rate=44100, is_default=True)
    ]
    mock.set_input_device.return_value = True
    mock.set_output_device.return_value = True
    mock.record_audio.return_value = Path("recorded_audio.wav")
    mock.play_audio.return_value = True
    mock.set_volume.return_value = True
    mock.get_audio_info.return_value = {
        "duration": 5.0,
        "sample_rate": 44100,
        "channels": 2,
        "format": "wav"
    }
    mock.get_service_status.return_value = {
        "status": "ready",
        "input_device": "Test Input",
        "output_device": "Test Output"
    }
    return mock


class TestAPIEndpoints:
    """Test suite for API endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "VTuber Backend API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data

    @patch('aichat.backend.routes.chat.db_ops')
    @patch('aichat.backend.routes.chat.get_chat_service')
    def test_list_characters(self, mock_get_chat_service, mock_db_ops, client, mock_character, mock_chat_service):
        """Test list characters endpoint"""
        mock_get_chat_service.return_value = mock_chat_service
        mock_db_ops.list_characters.return_value = [Mock(**mock_character)]
        
        response = client.get("/api/chat/characters")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test_character"

    @patch('aichat.backend.routes.chat.db_ops')
    @patch('aichat.backend.routes.chat.get_chat_service')
    def test_get_character(self, mock_get_chat_service, mock_db_ops, client, mock_character, mock_chat_service):
        """Test get character by ID endpoint"""
        mock_get_chat_service.return_value = mock_chat_service
        mock_db_ops.get_character.return_value = Mock(**mock_character)
        
        response = client.get("/api/chat/characters/1")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_character"
        assert data["id"] == 1

    @patch('aichat.backend.routes.chat.db_ops')
    @patch('aichat.backend.routes.chat.get_chat_service')
    @patch('aichat.backend.routes.chat.emit_chat_response')
    def test_chat_with_character(self, mock_emit, mock_get_chat_service, mock_db_ops, client, mock_character, mock_chat_service):
        """Test chat with character endpoint"""
        mock_get_chat_service.return_value = mock_chat_service
        mock_db_ops.get_character_by_name.return_value = Mock(**mock_character)
        mock_db_ops.create_chat_log.return_value = None
        mock_emit.return_value = None
        
        chat_message = {
            "text": "Hello, how are you?",
            "character": "test_character"
        }
        
        response = client.post("/api/chat/chat", json=chat_message)
        assert response.status_code == 200
        data = response.json()
        assert data["user_input"] == "Hello, how are you?"
        assert data["character"] == "test_character"
        assert data["response"] == "Hello! How can I help you?"

    @patch('aichat.backend.routes.chat.db_ops')
    @patch('aichat.backend.routes.chat.get_chat_service')
    @patch('aichat.backend.routes.chat.get_event_system')
    def test_switch_character(self, mock_get_event_system, mock_get_chat_service, mock_db_ops, client, mock_character, mock_chat_service):
        """Test switch character endpoint"""
        mock_get_chat_service.return_value = mock_chat_service
        mock_db_ops.get_character_by_name.return_value = Mock(**mock_character)
        mock_event_system = AsyncMock()
        mock_get_event_system.return_value = mock_event_system
        
        switch_request = {"character": "test_character"}
        
        response = client.post("/api/chat/switch_character", json=switch_request)
        assert response.status_code == 200
        data = response.json()
        assert data["character"] == "test_character"
        assert data["status"] == "switched"

    @patch('aichat.backend.routes.chat.db_ops')
    @patch('aichat.backend.routes.chat.get_chat_service')
    def test_text_to_speech(self, mock_get_chat_service, mock_db_ops, client, mock_character, mock_chat_service):
        """Test text-to-speech endpoint"""
        mock_get_chat_service.return_value = mock_chat_service
        mock_db_ops.get_character_by_name.return_value = Mock(**mock_character)
        
        tts_request = {
            "text": "Hello, this is a test",
            "character": "test_character"
        }
        
        response = client.post("/api/chat/tts", json=tts_request)
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Hello, this is a test"
        assert data["character"] == "test_character"
        assert data["audio_format"] == "wav"

    @patch('aichat.backend.routes.chat.get_whisper_service')
    def test_speech_to_text(self, mock_get_whisper_service, client, mock_whisper_service):
        """Test speech-to-text endpoint"""
        mock_get_whisper_service.return_value = mock_whisper_service
        
        # Create a mock file
        test_audio_content = b"fake audio content"
        
        response = client.post(
            "/api/chat/stt",
            files={"file": ("test_audio.wav", test_audio_content, "audio/wav")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Hello, this is a test transcription"
        assert data["language"] == "en"
        assert data["confidence"] == 0.95

    @patch('aichat.backend.routes.voice.get_audio_io_service_dep')
    def test_get_audio_devices(self, mock_get_audio_io_service, client, mock_audio_io_service):
        """Test get audio devices endpoint"""
        mock_get_audio_io_service.return_value = mock_audio_io_service
        
        response = client.get("/api/voice/audio/devices")
        assert response.status_code == 200
        data = response.json()
        assert "input_devices" in data
        assert "output_devices" in data
        assert len(data["input_devices"]) == 1
        assert data["input_devices"][0]["name"] == "Test Input"

    def test_chat_validation_empty_text(self, client):
        """Test chat endpoint with empty text validation"""
        chat_message = {
            "text": "",
            "character": "test_character"
        }
        
        response = client.post("/api/chat/chat", json=chat_message)
        assert response.status_code == 422  # Validation error

    def test_tts_validation_invalid_speed(self, client):
        """Test TTS endpoint with invalid speed validation"""
        tts_request = {
            "text": "Hello, this is a test",
            "character": "test_character",
            "speed": 3.0  # Invalid: > 2.0
        }
        
        response = client.post("/api/chat/tts", json=tts_request)
        assert response.status_code == 422  # Validation error


class TestChatterboxTTSIntegration:
    """Test Chatterbox TTS hardware detection and intensity streaming"""

    @pytest.fixture
    def mock_chatterbox_service(self):
        """Mock Chatterbox TTS service"""
        mock = AsyncMock()
        mock.device = "cpu"
        mock.cpu_fallback = True
        mock.model_loaded = True
        mock.get_device_info.return_value = {
            "device": "cpu",
            "cpu_fallback": True,
            "pytorch_available": True,
            "cuda_available": False,
            "gpu_name": None,
            "vram_gb": 0.0
        }
        mock.get_service_status.return_value = {
            "service": "chatterbox_tts",
            "device": "cpu",
            "device_info": mock.get_device_info.return_value,
            "model_loaded": True,
            "default_voice": "default",
            "supports_streaming": True,
            "punctuation_pauses": {".": 0.8, ",": 0.3},
            "status": "ready",
            "audio_io": {"status": "ready"},
            "cpu_fallback": True,
            "performance_mode": "CPU-optimized"
        }
        mock.generate_streaming_speech.return_value = [
            {
                "text": "Hello there!",
                "punctuation": "!",
                "pause_duration": 0.7,
                "audio_file": "chatterbox_0.wav",
                "is_final": False
            },
            {
                "text": "How are you today?",
                "punctuation": "?",
                "pause_duration": 0.7,
                "audio_file": "chatterbox_1.wav",
                "is_final": True
            }
        ]
        return mock

    @patch('aichat.backend.services.voice.tts.chatterbox_tts_service.ChatterboxTTSService')
    async def test_chatterbox_hardware_detection(self, mock_chatterbox_class, mock_chatterbox_service):
        """Test Chatterbox hardware detection"""
        mock_chatterbox_class.return_value = mock_chatterbox_service
        
        # Test service initialization
        service = mock_chatterbox_class()
        await service.initialize()
        
        # Verify device detection
        device_info = service.get_device_info()
        assert device_info["device"] == "cpu"
        assert device_info["cpu_fallback"] == True
        assert device_info["pytorch_available"] == True

    @patch('aichat.backend.services.voice.tts.chatterbox_tts_service.ChatterboxTTSService')
    async def test_chatterbox_streaming_speech(self, mock_chatterbox_class, mock_chatterbox_service):
        """Test Chatterbox streaming speech generation"""
        mock_chatterbox_class.return_value = mock_chatterbox_service
        
        service = mock_chatterbox_class()
        segments = await service.generate_streaming_speech(
            text="Hello there! How are you today?",
            character_name="TestCharacter",
            exaggeration=1.2
        )
        
        assert len(segments) == 2
        assert segments[0]["text"] == "Hello there!"
        assert segments[0]["punctuation"] == "!"
        assert segments[1]["is_final"] == True

    @patch('aichat.backend.services.llm.emotion_parser.IntensityParser')
    async def test_intensity_parsing(self, mock_intensity_parser_class):
        """Test intensity parsing for streaming"""
        mock_parser = Mock()
        mock_parser.extract_intensity_from_chunk.return_value = 1.2
        mock_parser.strip_intensity_marker.return_value = "Hello there!"
        mock_intensity_parser_class.return_value = mock_parser
        
        parser = mock_intensity_parser_class()
        
        # Test intensity extraction
        test_chunk = "[INTENSITY: high] Hello there!"
        intensity = parser.extract_intensity_from_chunk(test_chunk)
        clean_text = parser.strip_intensity_marker(test_chunk)
        
        assert intensity == 1.2
        assert clean_text == "Hello there!"


class TestSystemIntegration:
    """Test system-wide integration scenarios"""

    @patch('aichat.backend.services.chat.service_manager.get_chat_service')
    @patch('aichat.backend.services.voice.tts.chatterbox_tts_service.ChatterboxTTSService')
    @patch('aichat.backend.services.llm.tools.simple_llm_service.SimpleLLMService')
    async def test_full_chat_to_tts_pipeline(self, mock_llm_service_class, mock_chatterbox_class, mock_chat_service):
        """Test complete pipeline from chat to TTS with intensity"""
        # Setup mocks
        mock_llm_service = AsyncMock()
        mock_llm_service.process_streaming_with_intensity_first.return_value = [
            (1.2, "Hello there!"),
            (None, " How can I help you today?")
        ]
        mock_llm_service_class.return_value = mock_llm_service
        
        mock_chatterbox = AsyncMock()
        mock_chatterbox.generate_streaming_speech_with_intensity.return_value = [
            {
                "text": "Hello there! How can I help you today?",
                "exaggeration": 1.2,
                "audio_file": "output.wav",
                "character": "TestCharacter"
            }
        ]
        mock_chatterbox_class.return_value = mock_chatterbox
        
        # Test pipeline
        llm_service = mock_llm_service_class()
        tts_service = mock_chatterbox_class()
        
        # Simulate LLM streaming with intensity
        intensity_chunks = []
        async for exaggeration, text_chunk in llm_service.process_streaming_with_intensity_first(
            "Hello, I'm excited to learn!", 
            Mock(name="TestCharacter", personality="helpful")
        ):
            intensity_chunks.append((exaggeration, text_chunk))
        
        # Extract final intensity and text
        final_intensity = intensity_chunks[0][0] if intensity_chunks else 0.7
        full_text = "".join(chunk[1] for chunk in intensity_chunks if chunk[1])
        
        # Generate TTS with consistent intensity
        async def text_generator():
            yield full_text
        
        audio_segments = []
        async for segment in tts_service.generate_streaming_speech_with_intensity(
            text_generator(), "TestCharacter", final_intensity
        ):
            audio_segments.append(segment)
        
        # Verify pipeline results
        assert len(intensity_chunks) == 2
        assert final_intensity == 1.2
        assert len(audio_segments) == 1
        assert audio_segments[0]["exaggeration"] == 1.2

    async def test_error_handling_scenarios(self):
        """Test various error handling scenarios"""
        with patch('aichat.backend.routes.chat.db_ops') as mock_db_ops:
            mock_db_ops.get_character_by_name.return_value = None
            
            # Test character not found
            client = TestClient(create_app())
            response = client.post("/api/chat/chat", json={
                "text": "Hello",
                "character": "nonexistent_character"
            })
            assert response.status_code == 404

    def test_openapi_schema_generation(self, app):
        """Test that OpenAPI schema is properly generated"""
        client = TestClient(app)
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "VTuber Backend API"
        
        # Verify our endpoints are documented
        paths = schema["paths"]
        assert "/api/chat/chat" in paths
        assert "/api/chat/tts" in paths
        assert "/api/voice/audio/devices" in paths


@pytest.mark.asyncio
async def test_async_operations():
    """Test async operations work correctly"""
    from aichat.backend.services.llm.emotion_parser import IntensityParser
    
    parser = IntensityParser()
    
    # Test intensity extraction
    test_cases = [
        ("[INTENSITY: high] I'm excited!", 1.2),
        ("[INTENSITY: low] I'm feeling quiet", 0.3),
        ("[INTENSITY: theatrical] AMAZING!", 2.0),
        ("No intensity marker here", None)
    ]
    
    for text, expected_intensity in test_cases:
        result = parser.extract_intensity_from_chunk(text)
        if expected_intensity is None:
            assert result is None
        else:
            assert abs(result - expected_intensity) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
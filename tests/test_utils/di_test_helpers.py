"""
Test Utilities for Dependency Injection

Provides helper utilities for testing with the new DI container,
including easy mocking, test containers, and service substitution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, Type, TypeVar, Union
from contextlib import contextmanager

from aichat.backend.services.di_container import DIContainer, Lifetime

T = TypeVar('T')

class TestDIContainer(DIContainer):
    """Test-specific DI container with easy mocking capabilities"""
    
    def __init__(self):
        super().__init__()
        self._test_overrides: Dict[Union[Type, str], Any] = {}
    
    def register_test_mock(self, service_type: Union[Type[T], str], mock_instance: T) -> 'TestDIContainer':
        """Register a mock instance for testing"""
        self._test_overrides[service_type] = mock_instance
        self.register_instance(service_type, mock_instance)
        return self
    
    def clear_test_overrides(self):
        """Clear all test overrides"""
        for service_type in self._test_overrides.keys():
            if service_type in self._services:
                del self._services[service_type]
            if service_type in self._singletons:
                del self._singletons[service_type]
        self._test_overrides.clear()

@pytest.fixture
def test_di_container():
    """Provide a clean test DI container with REAL services but mocked dependencies"""
    container = TestDIContainer()
    
    # Register real services with mocked dependencies
    from aichat.backend.services.chat.chat_service import ChatService
    from aichat.backend.services.voice.stt.whisper_service import WhisperService
    from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
    from aichat.backend.services.audio.audio_io_service import AudioIOService
    
    # Register REAL services, not mocks
    container.register_singleton("chat_service", ChatService)
    container.register_singleton("whisper_service", WhisperService) 
    container.register_singleton("chatterbox_tts_service", ChatterboxTTSService)
    container.register_singleton("audio_io_service", AudioIOService)
    
    yield container
    
    # Cleanup
    container.clear_test_overrides()

def create_mock_whisper_service():
    """Create a mock WhisperService for testing"""
    mock = AsyncMock()
    mock.transcribe_audio.return_value = {
        "text": "Hello world",
        "language": "en", 
        "confidence": 0.95,
        "processing_time": 0.5
    }
    mock.transcribe_microphone.return_value = {
        "text": "Test transcription",
        "language": "en",
        "confidence": 0.88,
        "processing_time": 1.2
    }
    mock.transcribe_audio_bytes.return_value = {
        "text": "Byte transcription",
        "confidence": 0.92
    }
    return mock

def create_mock_tts_service():
    """Create a mock ChatterboxTTSService for testing"""
    mock = AsyncMock()
    mock.generate_speech.return_value = "/tmp/test_speech.wav"
    mock.generate_streaming_speech.return_value = [
        {"text": "Hello!", "audio_file": "/tmp/seg1.wav", "pause_duration": 0.7},
        {"text": "How are you?", "audio_file": "/tmp/seg2.wav", "pause_duration": 0.7}
    ]
    # Make this a regular mock since it's not async
    mock.split_text_by_punctuation = MagicMock(return_value=[
        {"text": "Test sentence.", "punctuation": ".", "pause_duration": 0.8, "is_final": True}
    ])
    mock.get_service_status.return_value = {
        "service": "chatterbox_tts", 
        "status": "ready",
        "device": "cpu"
    }
    return mock

def create_mock_audio_io_service():
    """Create a mock AudioIOService for testing"""
    mock = AsyncMock()
    mock.get_input_devices.return_value = [
        MagicMock(id=1, name="Test Mic", channels=1, sample_rate=44100, is_default=True)
    ]
    mock.get_output_devices.return_value = [
        MagicMock(id=1, name="Test Speaker", channels=2, sample_rate=44100, is_default=True)  
    ]
    mock.record_audio.return_value = "/tmp/recorded.wav"
    mock.play_audio.return_value = True
    mock.get_service_status.return_value = {
        "status": "active",
        "backend": "pyaudio",
        "devices": {"input": {"count": 1}, "output": {"count": 1}}
    }
    return mock

def create_mock_chat_service():
    """Create a mock ChatService that behaves like the real service"""
    mock = AsyncMock()
    
    # Set up realistic behavior
    mock._current_character_id = 1
    
    # process_message method
    mock.process_message.return_value = MagicMock(
        response="Hello! How can I help?",
        emotion="happy", 
        model_used="test-model"
    )
    
    # generate_tts method  
    mock.generate_tts.return_value = "/tmp/test_tts.wav"
    
    # switch_character method - has realistic logic
    async def mock_switch_character(character_id: int, character_name: str) -> bool:
        # Simulate the real behavior - check if character exists via db_ops
        try:
            from aichat.core.database import db_ops
            character = await db_ops.get_character(character_id)
            if character:
                mock._current_character_id = character_id
                return True
            return False
        except:
            # If db_ops is mocked, just return True for known characters
            if character_name in ["hatsune_miku", "test_character"]:
                mock._current_character_id = character_id
                return True
            return False
    
    mock.switch_character.side_effect = mock_switch_character
    
    # get_current_character method - matches real interface
    async def mock_get_current_character():
        if mock._current_character_id:
            return {
                "id": mock._current_character_id, 
                "name": "hatsune_miku",
                "profile": "A virtual singer",
                "personality": "cheerful"
            }
        return None
    
    mock.get_current_character.side_effect = mock_get_current_character
    
    return mock

@contextmanager
def mock_di_container(dependency_overrides: Dict[str, Any] = None):
    """Context manager for testing real services with mocked dependencies"""
    from aichat.backend.services import di_container
    from unittest.mock import patch
    
    # Save original container
    original_container = di_container._container
    
    # Create test container with REAL services
    from aichat.backend.services.chat.chat_service import ChatService
    from aichat.backend.services.voice.stt.whisper_service import WhisperService
    from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
    from aichat.backend.services.audio.audio_io_service import AudioIOService
    
    test_container = TestDIContainer()
    test_container.register_singleton("chat_service", ChatService)
    test_container.register_singleton("whisper_service", WhisperService) 
    test_container.register_singleton("chatterbox_tts_service", ChatterboxTTSService)
    test_container.register_singleton("audio_io_service", AudioIOService)
    
    # Set as global container
    di_container._container = test_container
    
    # Mock external dependencies that services depend on
    mock_db_ops = dependency_overrides.get('db_ops') if dependency_overrides else MockFactory.database_ops()
    mock_openrouter = dependency_overrides.get('openrouter') if dependency_overrides else AsyncMock()
    mock_event_system = dependency_overrides.get('event_system') if dependency_overrides else AsyncMock()
    
    patches = [
        patch('aichat.core.database.db_ops', mock_db_ops),
        patch('aichat.backend.routes.chat.db_ops', mock_db_ops),
        patch('aichat.backend.services.chat.chat_service.db_ops', mock_db_ops),
        patch('aichat.core.event_system.get_event_system', return_value=mock_event_system),
    ]
    
    try:
        for p in patches:
            p.__enter__()
        yield test_container
    finally:
        for p in reversed(patches):
            p.__exit__(None, None, None)
        # Restore original container
        di_container._container = original_container

class MockFactory:
    """Factory for creating common test mocks"""
    
    @staticmethod
    def character_dao():
        mock = AsyncMock()
        mock.get_by_id.return_value = MagicMock(
            id=1, name="test_char", profile="Test", personality="friendly"
        )
        mock.get_by_name.return_value = MagicMock(
            id=1, name="test_char", profile="Test", personality="friendly"
        )
        mock.list_all.return_value = [
            MagicMock(id=1, name="char1", profile="Test1"),
            MagicMock(id=2, name="char2", profile="Test2")
        ]
        return mock
    
    @staticmethod
    def event_system():
        mock = AsyncMock()
        mock.emit.return_value = None
        return mock
    
    @staticmethod
    def database_ops():
        """Create realistic database operations mock matching actual db_ops interface"""
        mock = AsyncMock()
        
        # Character operations (matching actual db_ops methods)
        # Use simple objects with proper attributes, not MagicMock
        from types import SimpleNamespace
        
        test_character = SimpleNamespace(
            id=1,
            name="hatsune_miku", 
            profile="A virtual singer",
            personality="cheerful",
            avatar_url=None
        )
        
        mock.list_characters.return_value = [test_character]
        mock.get_character.return_value = test_character
        
        # Make get_character_by_name return None for invalid characters
        def mock_get_character_by_name(name):
            if name in ["hatsune_miku", "test_character"]:
                return test_character
            return None
        mock.get_character_by_name.side_effect = mock_get_character_by_name
        
        # Chat operations
        from datetime import datetime
        mock.create_chat_log.return_value = MagicMock(id=1)
        mock.get_chat_logs.return_value = [
            MagicMock(
                id=1,
                character_id=1,
                user_message="Hi",
                character_response="Hello!",
                timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),  # Use datetime object
                emotion="happy",
                metadata={}
            )
        ]
        
        # Voice model operations
        mock.list_voice_models.return_value = [
            MagicMock(id=1, name="hatsune_miku", model_path="/models/miku.onnx")
        ]
        
        mock.list_training_data.return_value = [
            MagicMock(id=1, filename="sample.wav", transcript="Hello", duration=1.0)
        ]
        
        mock.create_training_data.return_value = MagicMock(id=2, filename="new_sample.wav")
        
        return mock


@contextmanager
def patch_db_ops(mock_db_ops=None):
    """Context manager to patch db_ops directly"""
    from unittest.mock import patch
    
    if mock_db_ops is None:
        mock_db_ops = MockFactory.database_ops()
    
    with patch('aichat.core.database.db_ops', mock_db_ops), \
         patch('aichat.backend.routes.chat.db_ops', mock_db_ops), \
         patch('aichat.backend.services.chat.chat_service.db_ops', mock_db_ops):
        yield mock_db_ops

# Pytest fixtures for common mocks
@pytest.fixture
def mock_whisper_service():
    return create_mock_whisper_service()

@pytest.fixture
def mock_tts_service():
    return create_mock_tts_service()

@pytest.fixture
def mock_audio_io_service():
    return create_mock_audio_io_service()

@pytest.fixture
def mock_chat_service():
    return create_mock_chat_service()

@pytest.fixture
def mock_character_dao():
    return MockFactory.character_dao()

@pytest.fixture
def mock_event_system():
    return MockFactory.event_system()

@pytest.fixture
def mock_db_ops():
    return MockFactory.database_ops()

# Test client with DI container mocking
@pytest.fixture
def test_client_with_mocks():
    """Test client with pre-configured service mocks"""
    from fastapi.testclient import TestClient
    from aichat.backend.main import create_app
    
    overrides = {
        "whisper_service": create_mock_whisper_service(),
        "chatterbox_tts_service": create_mock_tts_service(),
        "audio_io_service": create_mock_audio_io_service(),
        "chat_service": create_mock_chat_service()
    }
    
    with mock_di_container(overrides) as container:
        app = create_app()
        client = TestClient(app)
        yield client, container
"""
Example of Modernized Test Using New DI Architecture

This shows how to write tests using the new dependency injection container
instead of the old singleton-based service factory.

BEFORE: Old test style with manual mocking and path issues
AFTER: New test style with DI container and proper service injection
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Import from new structure
from aichat.backend.main import create_app
from aichat.backend.routes.chat import router
from aichat.models.schemas import ChatMessage, TTSRequest

# Import test utilities
from tests.test_utils.di_test_helpers import (
    test_di_container, 
    mock_di_container,
    create_mock_chat_service,
    create_mock_tts_service,
    MockFactory
)

class TestChatRoutesModern:
    """Modern chat routes tests using DI container"""
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_with_di_container(self, test_di_container):
        """Test chat endpoint using DI container with mocks"""
        
        # The test_di_container fixture automatically provides mocked services
        app = create_app()
        client = TestClient(app)
        
        # Mock database response
        with mock_di_container({
            "chat_service": create_mock_chat_service()
        }) as container:
            
            # Configure mock behavior
            chat_service = container.resolve("chat_service")
            chat_service.process_message.return_value = MagicMock(
                response="Test response",
                emotion="happy",
                model_used="test-model"
            )
            
            # Test request
            response = client.post("/api/chat/chat", json={
                "text": "Hello!",
                "character": "test_character"
            })
            
            # Assertions
            assert response.status_code == 200  # or 404 if no character data
            
            # Verify service was called correctly
            if response.status_code == 200:
                data = response.json()
                assert data["user_input"] == "Hello!"
                assert data["character"] == "test_character"
    
    @pytest.mark.asyncio
    async def test_tts_endpoint_with_new_service(self, test_di_container):
        """Test TTS endpoint using new ChatterboxTTS service"""
        
        app = create_app()
        client = TestClient(app)
        
        # Override TTS service behavior
        with mock_di_container({
            "chatterbox_tts_service": create_mock_tts_service()
        }) as container:
            
            tts_service = container.resolve("chatterbox_tts_service")
            tts_service.generate_speech.return_value = "/tmp/test_audio.wav"
            
            response = client.post("/api/chat/tts", json={
                "text": "Hello world! This is a test.",
                "character": "test_character"
            })
            
            # Should work with mocked services even if character doesn't exist
            # The DI container provides the mock service
            
            if response.status_code == 200:
                data = response.json()
                assert data["text"] == "Hello world! This is a test."
                assert data["character"] == "test_character"
            
            # Verify TTS service was called with correct parameters
            tts_service.generate_speech.assert_called_once()

class TestServicesDirect:
    """Test services directly with DI container"""
    
    @pytest.mark.asyncio
    async def test_chat_service_with_dependencies(self, test_di_container):
        """Test ChatService with injected dependencies"""
        
        # Get service from DI container (will have mocked dependencies)
        chat_service = test_di_container.resolve("chat_service")
        
        # Test service method
        result = await chat_service.process_message(
            "Hello", 1, "test_character"
        )
        
        assert result.response == "Hello! How can I help?"
        assert result.emotion == "happy"
        assert result.model_used == "test-model"
    
    @pytest.mark.asyncio
    async def test_tts_service_segmentation(self, test_di_container):
        """Test TTS service segmentation improvements"""
        
        tts_service = test_di_container.resolve("chatterbox_tts_service")
        
        # Test sentence-based segmentation
        segments = list(tts_service.split_text_by_punctuation(
            "Hello there! How are you? I hope you're well."
        ))
        
        # With mocked service, this returns the mock data
        assert len(segments) == 1  # Mock returns 1 segment
        assert segments[0]["text"] == "Test sentence."

class TestIntegrationWithRealServices:
    """Integration tests that use real services through DI container"""
    
    @pytest.mark.asyncio
    async def test_real_tts_service_integration(self):
        """Test with real TTS service (if needed for integration tests)"""
        from aichat.backend.services.di_container import get_container
        
        # Get real container (not test container)
        container = get_container()
        
        # This will get the real ChatterboxTTSService
        tts_service = container.resolve("chatterbox_tts_service")
        
        # Test real segmentation
        segments = list(tts_service.split_text_by_punctuation(
            "Hello! How are you? Fine, thanks."
        ))
        
        # Real service should create multiple segments
        assert len(segments) >= 2  # At least 2 sentences
        assert any("Hello!" in seg["text"] for seg in segments)

# Example of testing with custom service configuration
@pytest.mark.asyncio
async def test_custom_service_config():
    """Example of testing with custom service configuration"""
    from aichat.backend.services.di_container import DIContainer, Lifetime
    
    # Create custom container for this test
    container = DIContainer()
    
    # Register custom mock with specific behavior
    custom_tts = AsyncMock()
    custom_tts.generate_speech.return_value = "/custom/path.wav"
    
    container.register_instance("chatterbox_tts_service", custom_tts)
    
    # Use custom container
    service = container.resolve("chatterbox_tts_service")
    result = await service.generate_speech("test", "char")
    
    assert result == "/custom/path.wav"

# Example of testing service lifetimes
def test_service_lifetimes():
    """Test that service lifetimes work correctly"""
    from aichat.backend.services.di_container import get_container
    
    container = get_container()
    
    # Singletons should return same instance
    tts1 = container.resolve("chatterbox_tts_service")
    tts2 = container.resolve("chatterbox_tts_service")
    assert tts1 is tts2  # Same instance
    
    # Scoped services should return same instance within scope
    chat1 = container.resolve("chat_service") 
    chat2 = container.resolve("chat_service")
    assert chat1 is chat2  # Same instance in scope
    
    # After clearing scope, should get new instance
    container.clear_scoped()
    chat3 = container.resolve("chat_service")
    assert chat1 is not chat3  # Different instance after scope clear
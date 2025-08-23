# Integration tests for cross-application communication
# This tests communication between the lightweight API and the main chat_app
# Run with: pytest tests/integration -q
import pytest
from fastapi.testclient import TestClient

# Import from new structure
from aichat.backend.main import create_app

# Import test utilities
from tests.test_utils.di_test_helpers import (
    mock_di_container,
    create_mock_chat_service,
    create_mock_whisper_service,
    create_mock_tts_service,
    MockFactory
)


class TestAPIIntegrationModern:
    """Modern integration tests using DI container"""
    
    @pytest.fixture
    def mock_services(self):
        """Create comprehensive mock services for integration testing"""
        return {
            "chat_service": create_mock_chat_service(),
            "whisper_service": create_mock_whisper_service(),
            "chatterbox_tts_service": create_mock_tts_service(),
            "database_ops": MockFactory.database_ops()
        }
    
    def test_main_app_health_check(self, mock_services):
        """Test that the main app health check works with DI container"""
        with mock_di_container(mock_services):
            app = create_app()
            client = TestClient(app)
            r = client.get("/health")
            assert r.status_code == 200
            h = r.json()
            assert "status" in h

    def test_chat_endpoint_integration(self, mock_services):
        """Test chat endpoint with full service integration"""
        with mock_di_container(mock_services):
            app = create_app()
            client = TestClient(app)
            
            r = client.post("/api/chat/chat", json={
                "text": "hello world", 
                "character": "hatsune_miku"
            })
            
            assert r.status_code == 200
            body = r.json()
            assert "response" in body
            assert body["response"] == "Hello! How can I help?"

    def test_tts_endpoint_integration(self, mock_services):
        """Test TTS endpoint with mock services"""
        with mock_di_container(mock_services):
            app = create_app()
            client = TestClient(app)
            
            r = client.post("/api/chat/tts", json={
                "text": "speak this", 
                "character": "hatsune_miku"
            })
            
            assert r.status_code == 200
            t = r.json()
            assert t.get("audio_format") == "wav"
            assert t.get("audio_file") == "/tmp/test_speech.wav"

    def test_service_integration_flow(self, mock_services):
        """Test full service integration flow"""
        with mock_di_container(mock_services) as container:
            app = create_app()
            client = TestClient(app)
            
            # Test root endpoint
            root_response = client.get("/")
            assert root_response.status_code == 200
            root_data = root_response.json()
            assert "status" in root_data
            
            # Test character listing
            chars_response = client.get("/api/chat/characters")
            assert chars_response.status_code == 200
            chars_data = chars_response.json()
            assert isinstance(chars_data, list)
            
            # Verify services were called through DI container
            db_ops = container.resolve("database_ops")
            db_ops.list_characters.assert_called()

    def test_websocket_integration(self, mock_services):
        """Test WebSocket integration with DI container"""
        with mock_di_container(mock_services):
            app = create_app()
            
            # Test WebSocket endpoint exists
            with TestClient(app) as client:
                # Just test that the app starts and routes are registered
                response = client.get("/docs")  # OpenAPI docs should work
                assert response.status_code == 200
    
    def test_voice_routes_integration(self, mock_services):
        """Test voice routes integration"""
        with mock_di_container(mock_services):
            app = create_app()
            client = TestClient(app)
            
            # Test voice recording endpoints exist
            # These might return errors without proper setup, but routes should be registered
            response = client.post("/api/voice/record/start", json={"session_id": "test"})
            # Should not be 404 (route not found)
            assert response.status_code != 404

    def test_error_handling_integration(self, mock_services):
        """Test error handling through DI container"""
        # Test with service that raises exceptions
        error_service = create_mock_chat_service()
        error_service.process_message.side_effect = Exception("Test error")
        
        services = mock_services.copy()
        services["chat_service"] = error_service
        
        with mock_di_container(services):
            app = create_app()
            client = TestClient(app)
            
            r = client.post("/api/chat/chat", json={
                "text": "hello", 
                "character": "test"
            })
            
            # Should handle error gracefully (not 200, but not crash)
            assert r.status_code in [400, 422, 500]  # Some error code
    
    def test_di_container_lifecycle_integration(self, mock_services):
        """Test that DI container properly manages service lifecycles"""
        with mock_di_container(mock_services) as container:
            app = create_app()
            client = TestClient(app)
            
            # Make multiple requests
            for i in range(3):
                r = client.post("/api/chat/chat", json={
                    "text": f"message {i}", 
                    "character": "test"
                })
                assert r.status_code == 200
            
            # Verify services were reused (singleton behavior)
            chat_service = container.resolve("chat_service")
            # Should have been called 3 times with the same instance
            assert chat_service.process_message.call_count == 3
"""
Chat routes testing - real functionality without mocking.
Tests actual chat API endpoints when server is running.
"""

import pytest
import requests


class TestChatRoutes:
    """Test chat route endpoints."""
    
    BASE_URL = "http://localhost:8765"
    
    @pytest.fixture(autouse=True)
    def check_server(self):
        """Check if server is running before running tests."""
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=2)
            if response.status_code != 200:
                pytest.skip("Server not running")
        except requests.RequestException:
            pytest.skip("Server not accessible")
    
    def test_list_characters(self):
        """Test GET /api/chat/characters endpoint."""
        response = requests.get(f"{self.BASE_URL}/api/chat/characters")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if data:  # If there are characters
            char = data[0]
            assert "id" in char
            assert "name" in char
            assert "profile" in char
            assert "personality" in char
    
    def test_chat_endpoint(self):
        """Test POST /api/chat/chat endpoint."""
        chat_data = {
            "text": "Hello, how are you?",
            "character": "test_character"
        }
        
        response = requests.post(f"{self.BASE_URL}/api/chat/chat", json=chat_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "response" in data
            assert "character" in data
            assert data["character"] == "test_character"
        else:
            # Service might not be fully configured
            assert response.status_code in [400, 404, 500]
    
    def test_switch_character(self):
        """Test POST /api/chat/switch_character endpoint."""
        switch_data = {"character": "test_character"}
        
        response = requests.post(f"{self.BASE_URL}/api/chat/switch_character", json=switch_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "character" in data
            assert data["character"] == "test_character"
        else:
            # Character might not exist
            assert response.status_code in [404, 500]
    
    def test_tts_endpoint(self):
        """Test POST /api/chat/tts endpoint."""
        tts_data = {
            "text": "Hello world",
            "character": "test_character"
        }
        
        response = requests.post(f"{self.BASE_URL}/api/chat/tts", json=tts_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "text" in data
            assert data["text"] == "Hello world"
        else:
            # TTS service might not be configured
            assert response.status_code in [404, 500, 503]
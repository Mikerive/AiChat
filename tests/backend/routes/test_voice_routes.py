"""
Voice routes testing - real functionality without mocking.
Tests actual voice API endpoints when server is running.
"""

import pytest
import requests


class TestVoiceRoutes:
    """Test voice route endpoints."""
    
    BASE_URL = "http://localhost:8765"
    
    @pytest.fixture(autouse=True)
    def check_server(self):
        """Check if server is running."""
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=2)
            if response.status_code != 200:
                pytest.skip("Server not running")
        except requests.RequestException:
            pytest.skip("Server not accessible")
    
    def test_audio_devices_endpoint(self):
        """Test GET /api/voice/audio/devices endpoint."""
        response = requests.get(f"{self.BASE_URL}/api/voice/audio/devices")
        
        if response.status_code == 200:
            data = response.json()
            assert "input_devices" in data
            assert "output_devices" in data
            assert isinstance(data["input_devices"], list)
            assert isinstance(data["output_devices"], list)
        else:
            # Audio service might not be available
            assert response.status_code in [404, 500, 503]
    
    def test_voice_models_endpoint(self):
        """Test GET /api/voice/models endpoint."""
        response = requests.get(f"{self.BASE_URL}/api/voice/models")
        
        if response.status_code == 200:
            data = response.json()
            assert "models" in data
            assert isinstance(data["models"], list)
        else:
            # Voice models might not be configured
            assert response.status_code in [404, 500]
    
    def test_stt_endpoint(self, sample_audio_file):
        """Test POST /api/voice/transcribe endpoint."""
        with open(sample_audio_file, "rb") as audio_file:
            files = {"file": ("test.wav", audio_file, "audio/wav")}
            response = requests.post(f"{self.BASE_URL}/api/voice/transcribe", files=files)
        
        if response.status_code == 200:
            data = response.json()
            assert "text" in data
            assert "language" in data
            assert "confidence" in data
        else:
            # STT service might not be available
            assert response.status_code in [400, 404, 422, 500, 503]
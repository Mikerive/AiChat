"""
Centralized API client for VTuber Frontend GUI

This module provides a clean interface for all backend API calls
used by the Streamlit GUI, with proper error handling and typing.
"""

import requests
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

class VTuberAPIClient:
    """Centralized API client for VTuber backend services"""
    
    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 10
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {e}")
            raise
    
    # System API routes
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and health check"""
        return self._make_request("GET", "/api/system/status")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information"""
        return self._make_request("GET", "/api/system/info")
    
    # Chat API routes  
    def send_chat_message(self, message: str, character_id: Optional[str] = None) -> Dict[str, Any]:
        """Send chat message to AI character"""
        data = {"message": message}
        if character_id:
            data["character_id"] = character_id
        return self._make_request("POST", "/api/chat/chat", json=data)
    
    def generate_tts(self, text: str, character_id: Optional[str] = None, voice_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate text-to-speech audio"""
        data = {"text": text}
        if character_id:
            data["character_id"] = character_id
        if voice_id:
            data["voice_id"] = voice_id
        return self._make_request("POST", "/api/chat/tts", json=data)
    
    def get_characters(self) -> Dict[str, Any]:
        """Get available AI characters"""
        return self._make_request("GET", "/api/chat/characters")
    
    def create_character(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new AI character"""
        return self._make_request("POST", "/api/chat/characters", json=character_data)
    
    # Voice/Audio API routes
    def get_audio_devices(self) -> Dict[str, Any]:
        """Get available audio input/output devices"""
        return self._make_request("GET", "/api/voice/audio/devices")
    
    def set_input_device(self, device_id: int) -> Dict[str, Any]:
        """Set audio input device"""
        return self._make_request("POST", f"/api/voice/audio/input-device/{device_id}")
    
    def set_output_device(self, device_id: int) -> Dict[str, Any]:
        """Set audio output device"""  
        return self._make_request("POST", f"/api/voice/audio/output-device/{device_id}")
    
    def record_audio(self, duration: float = 5.0) -> Dict[str, Any]:
        """Record audio from microphone"""
        return self._make_request("POST", "/api/voice/audio/record", params={"duration": duration})
    
    def play_audio(self, audio_path: str) -> Dict[str, Any]:
        """Play audio file"""
        return self._make_request("POST", "/api/voice/audio/play", json={"audio_path": audio_path})
    
    def set_volume(self, volume: float) -> Dict[str, Any]:
        """Set output volume (0.0 to 1.0)"""
        return self._make_request("POST", "/api/voice/audio/volume", json={"volume": volume})
    
    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """Get audio file information"""
        return self._make_request("GET", "/api/voice/audio/info", params={"audio_path": audio_path})
    
    def get_audio_status(self) -> Dict[str, Any]:
        """Get audio I/O service status"""
        return self._make_request("GET", "/api/voice/audio/status")
    
    def record_and_transcribe(self, duration: float = 5.0) -> Dict[str, Any]:
        """Record audio and transcribe with Whisper"""
        return self._make_request("POST", "/api/voice/audio/record-and-transcribe", 
                                json={"duration": duration})
    
    # Training/Job API routes
    def get_job_checkpoint(self, job_id: str) -> Dict[str, Any]:
        """Get training job checkpoint data"""
        return self._make_request("GET", f"/api/voice/jobs/{job_id}/checkpoint")
    
    def get_job_logs(self, job_id: str, tail: int = 200) -> Dict[str, Any]:
        """Get training job logs"""
        return self._make_request("GET", f"/api/voice/jobs/{job_id}/logs", 
                                params={"tail": tail})
    
    # Connectivity testing
    def test_connection(self) -> bool:
        """Test if backend is reachable and responding"""
        try:
            self.get_system_status()
            return True
        except:
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with all services"""
        results = {}
        
        # Test system status
        try:
            results["system"] = self.get_system_status()
            results["system"]["status"] = "healthy"
        except Exception as e:
            results["system"] = {"status": "error", "error": str(e)}
        
        # Test audio status
        try:
            results["audio"] = self.get_audio_status()
            results["audio"]["status"] = "healthy"
        except Exception as e:
            results["audio"] = {"status": "error", "error": str(e)}
        
        return results

# Convenience function for GUI usage
def create_api_client(api_host: str = "localhost", api_port: int = 8765) -> VTuberAPIClient:
    """Create API client instance"""
    base_url = f"http://{api_host}:{api_port}"
    return VTuberAPIClient(base_url)
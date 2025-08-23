"""
Backend Client - Communication with FastAPI backend
"""

import requests
import websocket
import json
import threading
import logging
from typing import Dict, Any, Optional, Callable
import time

logger = logging.getLogger(__name__)


class BackendClient:
    """Client for communicating with the FastAPI backend"""
    
    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url.rstrip('/')
        self.ws = None
        self.ws_thread = None
        self.message_handlers = {}
        self.is_connected = False
        
    def add_message_handler(self, event_type: str, handler: Callable):
        """Add handler for WebSocket messages"""
        if event_type not in self.message_handlers:
            self.message_handlers[event_type] = []
        self.message_handlers[event_type].append(handler)
        
    def remove_message_handler(self, event_type: str, handler: Callable):
        """Remove handler for WebSocket messages"""
        if event_type in self.message_handlers:
            try:
                self.message_handlers[event_type].remove(handler)
            except ValueError:
                pass
                
    def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        event_type = message.get('type')
        if event_type in self.message_handlers:
            for handler in self.message_handlers[event_type]:
                try:
                    handler(message.get('data'))
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")
                    
    # REST API methods - Character Management
    def get_characters(self) -> Dict[str, Any]:
        """Get list of available characters"""
        try:
            response = requests.get(f"{self.base_url}/api/chat/characters")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting characters: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def switch_character(self, character_name: str) -> Dict[str, Any]:
        """Switch to different character"""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat/switch_character",
                json={'character': character_name}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error switching character: {e}")
            return {'status': 'error', 'message': str(e)}
            
    # Audio Device Management
    def get_audio_devices(self) -> Dict[str, Any]:
        """Get available audio input/output devices"""
        try:
            response = requests.get(f"{self.base_url}/api/voice/audio/devices")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting audio devices: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def set_input_device(self, device_index: int) -> Dict[str, Any]:
        """Set audio input device"""
        try:
            response = requests.post(f"{self.base_url}/api/voice/audio/input-device/{device_index}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error setting input device: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def set_output_device(self, device_index: int) -> Dict[str, Any]:
        """Set audio output device"""
        try:
            response = requests.post(f"{self.base_url}/api/voice/audio/output-device/{device_index}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error setting output device: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def get_audio_status(self) -> Dict[str, Any]:
        """Get audio I/O service status"""
        try:
            response = requests.get(f"{self.base_url}/api/voice/audio/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting audio status: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def record_audio(self, duration: float = 5.0) -> Dict[str, Any]:
        """Record audio from microphone"""
        try:
            response = requests.post(
                f"{self.base_url}/api/voice/audio/record",
                params={'duration': duration}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def set_volume(self, volume: float) -> Dict[str, Any]:
        """Set output volume (0.0 to 1.0)"""
        try:
            response = requests.post(
                f"{self.base_url}/api/voice/audio/volume",
                json={'volume': volume}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return {'status': 'error', 'message': str(e)}
            
    def generate_tts(self, text: str, character_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate text-to-speech audio"""
        try:
            payload = {'text': text}
            if character_id:
                payload['character'] = character_id
            response = requests.post(
                f"{self.base_url}/api/chat/tts",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            return {'status': 'error', 'message': str(e)}
    
    # REST API methods - Chat
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        try:
            response = requests.get(f"{self.base_url}/api/system/status", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {"status": "error", "message": str(e)}
            
    def get_characters(self) -> Dict[str, Any]:
        """Get available characters"""
        try:
            response = requests.get(f"{self.base_url}/api/chat/characters", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get characters: {e}")
            return {"characters": []}
            
    def send_chat_message(self, message: str, character: str = "default") -> Dict[str, Any]:
        """Send chat message to backend"""
        try:
            payload = {"text": message, "character": character}
                
            response = requests.post(
                f"{self.base_url}/api/chat/chat",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send chat message: {e}")
            return {"status": "error", "message": str(e)}
            
    def get_audio_status(self) -> Dict[str, Any]:
        """Get audio system status"""
        try:
            response = requests.get(f"{self.base_url}/api/voice/audio/status", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get audio status: {e}")
            return {"status": "error", "message": str(e)}
            
    def start_voice_recording(self) -> Dict[str, Any]:
        """Start voice recording"""
        try:
            response = requests.post(f"{self.base_url}/api/voice/record/start", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to start voice recording: {e}")
            return {"status": "error", "message": str(e)}
            
    def stop_voice_recording(self) -> Dict[str, Any]:
        """Stop voice recording"""
        try:
            response = requests.post(f"{self.base_url}/api/voice/record/stop", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to stop voice recording: {e}")
            return {"status": "error", "message": str(e)}
            
    def synthesize_speech(self, text: str, character_id: str = None) -> Dict[str, Any]:
        """Synthesize speech from text"""
        try:
            payload = {"text": text}
            if character_id:
                payload["character_id"] = character_id
                
            response = requests.post(
                f"{self.base_url}/api/voice/synthesize",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to synthesize speech: {e}")
            return {"status": "error", "message": str(e)}
            
    # WebSocket methods
    def connect_websocket(self):
        """Connect to WebSocket for real-time events"""
        if self.is_connected:
            return
            
        try:
            ws_url = self.base_url.replace('http://', 'ws://').replace('https://', 'wss://')
            ws_url += '/api/ws'
            
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self._on_ws_message,
                on_error=self._on_ws_error,
                on_close=self._on_ws_close,
                on_open=self._on_ws_open
            )
            
            # Start WebSocket in separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            
    def disconnect_websocket(self):
        """Disconnect WebSocket"""
        self.is_connected = False
        if self.ws:
            self.ws.close()
            
    def _on_ws_open(self, ws):
        """WebSocket connection opened"""
        logger.info("WebSocket connected")
        self.is_connected = True
        
    def _on_ws_message(self, ws, message):
        """WebSocket message received"""
        try:
            data = json.loads(message)
            self._handle_message(data)
        except Exception as e:
            logger.error(f"Error parsing WebSocket message: {e}")
            
    def _on_ws_error(self, ws, error):
        """WebSocket error occurred"""
        logger.error(f"WebSocket error: {error}")
        self.is_connected = False
        
    def _on_ws_close(self, ws, close_status_code, close_msg):
        """WebSocket connection closed"""
        logger.info("WebSocket disconnected")
        self.is_connected = False
        
    def send_websocket_message(self, message: Dict[str, Any]):
        """Send message via WebSocket"""
        if self.ws and self.is_connected:
            try:
                self.ws.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
        else:
            logger.warning("WebSocket not connected, cannot send message")
            
    # Utility methods
    def test_connection(self) -> bool:
        """Test connection to backend"""
        try:
            response = requests.get(f"{self.base_url}/api/system/status", timeout=3)
            return response.status_code == 200
        except:
            return False
            
    def is_backend_running(self) -> bool:
        """Check if backend is running"""
        return self.test_connection()
        
    def get_backend_info(self) -> Dict[str, Any]:
        """Get detailed backend information"""
        try:
            status = self.get_system_status()
            audio = self.get_audio_status()
            characters = self.get_characters()
            
            return {
                "status": status,
                "audio": audio,
                "characters": characters,
                "connected": True
            }
        except Exception as e:
            return {
                "status": {"status": "error", "message": str(e)},
                "audio": {"status": "error"},
                "characters": {"characters": []},
                "connected": False
            }
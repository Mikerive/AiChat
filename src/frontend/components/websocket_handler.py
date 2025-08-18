"""
WebSocket handler component
"""

import asyncio
import json
import logging
import threading
import websockets
from typing import Optional, Dict, Any, Callable
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import get_settings

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """Handles WebSocket connections and messaging"""
    
    def __init__(self, main_app: Optional[Any] = None):
        self.main_app = main_app
        self.settings = get_settings()
        self.ws_url = f"ws://{self.settings.api_host}:{self.settings.api_port}/api/ws"
        self.ws_connection: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_thread: Optional[threading.Thread] = None
        self.connected = False
        self.message_handlers: Dict[str, Callable] = {}
        
        # Register default handlers
        self.register_handler("chat.message", self._handle_chat_message)
        self.register_handler("chat.response", self._handle_chat_response)
        self.register_handler("training.progress", self._handle_training_progress)
        self.register_handler("system.status", self._handle_system_status)
        self.register_handler("error.occurred", self._handle_error)
        
        # Audio streaming handlers
        self.register_handler("audio.captured", self._handle_audio_captured)
        self.register_handler("audio.transcribed", self._handle_audio_transcribed)
        self.register_handler("audio.generated", self._handle_audio_generated)
        self.register_handler("audio.processed", self._handle_audio_processed)
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register a message handler for a specific event type"""
        self.message_handlers[event_type] = handler
    
    def start(self):
        """Start WebSocket connection"""
        if self.ws_thread and self.ws_thread.is_alive():
            return
        
        self.ws_thread = threading.Thread(target=self._websocket_worker, daemon=True)
        self.ws_thread.start()
    
    def _websocket_worker(self):
        """WebSocket worker thread"""
        while True:
            try:
                asyncio.run(self._connect_websocket())
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.connected = False
                if self.main_app:
                    # Use a safer approach for cross-thread GUI updates
                    try:
                        self.main_app.root.after_idle(self.main_app.update_connection_status)
                    except RuntimeError:
                        # GUI might be closed or not in main loop
                        pass
            
            # Reconnect after delay
            import time
            time.sleep(5)
    
    async def _connect_websocket(self):
        """Connect to WebSocket"""
        async with websockets.connect(self.ws_url) as websocket:
            self.ws_connection = websocket
            self.connected = True
            if self.main_app:
                # Schedule GUI update on main thread
                try:
                    self.main_app.root.after_idle(self.main_app.update_connection_status)
                except RuntimeError:
                    # GUI might be closed or not in main loop
                    pass
            
            # Send subscription message
            subscription = {
                "type": "subscribe",
                "events": list(self.message_handlers.keys())
            }
            await websocket.send(json.dumps(subscription))
            
            # Listen for messages
            async for message in websocket:
                self.handle_message(message)
    
    def send_message(self, message: Dict[str, Any]):
        """Send message via WebSocket"""
        if self.ws_connection and self.connected:
            try:
                # Create a new event loop for this thread if needed
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Send the message
                if loop.is_running():
                    # If loop is already running, schedule the send
                    asyncio.create_task(self.ws_connection.send(json.dumps(message)))
                else:
                    # If loop is not running, run it directly
                    loop.run_until_complete(self.ws_connection.send(json.dumps(message)))
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
    
    def send_audio_stream(self, audio_data: bytes, stream_id: str):
        """Send audio stream data to backend according to flow diagram"""
        try:
            import base64
            
            # Encode audio data as base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Send audio stream message
            message = {
                "type": "audio_stream",
                "audio_data": audio_b64,
                "stream_id": stream_id
            }
            
            self.send_message(message)
            
            if self.main_app:
                self.main_app.add_log(f"Audio stream sent: {stream_id} ({len(audio_data)} bytes)")
                
        except Exception as e:
            logger.error(f"Error sending audio stream: {e}")
            if self.main_app:
                self.main_app.add_log(f"Error sending audio stream: {e}")
    
    def send_chat_message(self, text: str, character: str = "hatsune_miku"):
        """Send chat message via WebSocket"""
        message = {
            "type": "chat",
            "text": text,
            "character": character
        }
        self.send_message(message)
    
    def request_status(self):
        """Request system status"""
        message = {"type": "get_status"}
        self.send_message(message)
    
    def ping(self):
        """Send ping to keep connection alive"""
        message = {"type": "ping"}
        self.send_message(message)
    
    def disconnect(self):
        """Disconnect WebSocket"""
        self.connected = False
        if self.ws_connection:
            try:
                # Create a new event loop for this thread if needed
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the close operation
                if loop.is_running():
                    # If loop is already running, schedule the close
                    asyncio.create_task(self.ws_connection.close())
                else:
                    # If loop is not running, run it directly
                    loop.run_until_complete(self.ws_connection.close())
            except Exception as e:
                logger.error(f"Error closing WebSocket connection: {e}")
                # Force close the connection
                self.ws_connection = None
    
    # Default message handlers
    def _handle_chat_message(self, data: Dict[str, Any]):
        """Handle chat message event"""
        if self.main_app:
            self.main_app.add_chat_message("User", data.get("text", ""))
    
    def _handle_chat_response(self, data: Dict[str, Any]):
        """Handle chat response event"""
        if self.main_app:
            self.main_app.add_chat_message("Character", data.get("response", ""))
    
    def _handle_training_progress(self, data: Dict[str, Any]):
        """Handle training progress event"""
        if self.main_app:
            self.main_app.add_training_progress(data)
    
    def _handle_system_status(self, data: Dict[str, Any]):
        """Handle system status event"""
        if self.main_app:
            self.main_app.update_system_status(data)
    
    def _handle_error(self, data: Dict[str, Any]):
        """Handle error event"""
        if self.main_app:
            self.main_app.add_log(f"Error: {data.get('message', 'Unknown error')}")
    
    # Audio streaming event handlers according to flow diagram
    def _handle_audio_captured(self, data: Dict[str, Any]):
        """Handle audio capture event from flow diagram"""
        if self.main_app:
            stream_id = data.get('stream_id', 'unknown')
            audio_size = data.get('audio_size', 0)
            self.main_app.add_log(f"Audio captured: {stream_id} ({audio_size} bytes)")
    
    def _handle_audio_transcribed(self, data: Dict[str, Any]):
        """Handle speech-to-text transcription event from Whisper STT Service"""
        if self.main_app:
            stream_id = data.get('stream_id', 'unknown')
            text = data.get('text', '')
            confidence = data.get('confidence', 0.0)
            language = data.get('language', 'unknown')
            
            self.main_app.add_log(f"Transcription complete ({stream_id}): {text} (confidence: {confidence:.2f})")
            
            # Update chat display with transcribed text
            if hasattr(self.main_app, 'chat_tab') and text:
                self.main_app.chat_tab.add_chat_message("You (Voice)", text)
    
    def _handle_audio_generated(self, data: Dict[str, Any]):
        """Handle TTS audio generation event from Piper TTS Service"""
        if self.main_app:
            stream_id = data.get('stream_id', 'unknown')
            audio_file = data.get('audio_file', '')
            character = data.get('character', 'unknown')
            text = data.get('text', '')
            
            self.main_app.add_log(f"TTS audio generated ({stream_id}): {character} - {audio_file}")
            
            # Notify main app about available audio file
            if hasattr(self.main_app, 'handle_audio_ready'):
                self.main_app.handle_audio_ready(audio_file, stream_id)
    
    def _handle_audio_processed(self, data: Dict[str, Any]):
        """Handle general audio processing event"""
        if self.main_app:
            processing_type = data.get('processing_type', 'unknown')
            stream_id = data.get('stream_id', 'unknown')
            self.main_app.add_log(f"Audio processed ({stream_id}): {processing_type}")
    
    def handle_transcription_complete(self, message: str):
        """Handle transcription complete event from WebSocket"""
        try:
            data = json.loads(message) if isinstance(message, str) else message
            
            if data.get("type") == "transcription" and data.get("event") == "transcription_complete":
                stream_id = data.get("stream_id", "unknown")
                text = data.get("text", "")
                confidence = data.get("confidence", 0.0)
                
                if self.main_app:
                    self.main_app.add_log(f"STT Complete ({stream_id}): {text}")
                    
                    # Add to chat display
                    if hasattr(self.main_app, 'chat_tab') and text:
                        self.main_app.chat_tab.add_chat_message("You (Voice)", text)
        
        except Exception as e:
            logger.error(f"Error handling transcription complete: {e}")
    
    def handle_chat_complete(self, message: str):
        """Handle complete chat response with TTS audio"""
        try:
            data = json.loads(message) if isinstance(message, str) else message
            
            if data.get("type") == "chat_complete" and data.get("event") == "response_ready":
                stream_id = data.get("stream_id", "unknown")
                user_input = data.get("user_input", "")
                character_response = data.get("character_response", "")
                emotion = data.get("emotion", "neutral")
                audio_file = data.get("audio_file", "")
                
                if self.main_app:
                    self.main_app.add_log(f"Chat Complete ({stream_id}): Response ready with audio")
                    
                    # Add character response to chat
                    if hasattr(self.main_app, 'chat_tab'):
                        self.main_app.chat_tab.add_chat_message("Character", character_response)
                    
                    # Handle audio file if available
                    if audio_file and hasattr(self.main_app, 'handle_audio_ready'):
                        self.main_app.handle_audio_ready(audio_file, stream_id)
        
        except Exception as e:
            logger.error(f"Error handling chat complete: {e}")
    
    def handle_message(self, message: str):
        """Enhanced message handler for audio streaming flow"""
        try:
            data = json.loads(message)
            message_type = data.get("type", "")
            event_type = data.get("event_type", "")
            
            # Handle special message types according to flow diagram
            if message_type == "transcription":
                self._schedule_gui_update(lambda: self.handle_transcription_complete(data))
                return
            elif message_type == "chat_complete":
                self._schedule_gui_update(lambda: self.handle_chat_complete(data))
                return
            elif message_type == "error":
                error_msg = data.get("message", "Unknown error")
                if self.main_app:
                    self._schedule_gui_update(lambda: self.main_app.add_log(f"WebSocket Error: {error_msg}"))
                return
            elif message_type == "pong":
                # Handle ping/pong
                if self.main_app:
                    self._schedule_gui_update(lambda: self.main_app.add_log("WebSocket: Connection alive"))
                return
            
            # Handle regular event-based messages
            message_text = data.get("message", "")
            
            # Add to logs if main app is available
            if self.main_app:
                self._schedule_gui_update(lambda: self.main_app.add_log(f"WS: {event_type} - {message_text}"))
            
            # Handle specific event types
            handler = self.message_handlers.get(event_type)
            if handler:
                self._schedule_gui_update(lambda: handler(data.get("data", {})))
            
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            if self.main_app:
                self._schedule_gui_update(lambda: self.main_app.add_log(f"WebSocket message error: {e}"))

    def _schedule_gui_update(self, callback):
        """Schedule a GUI update on the main thread"""
        if self.main_app and hasattr(self.main_app, 'root'):
            try:
                self.main_app.root.after_idle(callback)
            except RuntimeError:
                # GUI might be closed or not in main loop
                pass
"""
Whisper service for speech-to-text functionality
"""

import logging
import time
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np
import soundfile as sf

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from event_system import get_event_system, EventType, EventSeverity

logger = logging.getLogger(__name__)


class WhisperService:
    """Service for handling Whisper speech-to-text functionality"""
    
    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.model = None
        self.event_system = get_event_system()
        self._initialized = False
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Whisper model"""
        try:
            # Try to import whisper
            import whisper
            
            # Load model
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            self._initialized = True
            
            logger.info("Whisper model loaded successfully")
            
            # Emit model loaded event (async-safe)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.event_system.emit(
                        EventType.MODEL_LOADED,
                        f"Whisper model '{self.model_name}' loaded",
                        {"model_name": self.model_name, "device": "cpu"}
                    ))
                else:
                    loop.run_until_complete(self.event_system.emit(
                        EventType.MODEL_LOADED,
                        f"Whisper model '{self.model_name}' loaded",
                        {"model_name": self.model_name, "device": "cpu"}
                    ))
            except Exception:
                # If event system fails, continue without it
                pass
            
        except ImportError:
            logger.warning("Whisper not installed. Using mock service.")
            self._initialized = False
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            self.event_system.emit(
                EventType.MODEL_FAILED,
                f"Failed to load Whisper model: {e}",
                {"model_name": self.model_name},
                EventSeverity.ERROR
            )
            self._initialized = False
    
    async def transcribe_audio(self, audio_path: Path) -> Dict[str, Any]:
        """Transcribe audio file using Whisper"""
        try:
            if not self._initialized:
                # Return mock transcription
                return self._get_mock_transcription(audio_path)
            
            # Load audio file
            audio, sample_rate = sf.read(str(audio_path))
            
            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            # Transcribe
            start_time = time.time()
            result = self.model.transcribe(audio, language="en")
            processing_time = time.time() - start_time
            
            # Extract duration
            duration = len(audio) / sample_rate
            
            logger.info(f"Transcription completed: {result['text'][:100]}...")
            
            # Emit transcription event
            await self.event_system.emit(
                EventType.AUDIO_TRANSCRIBED,
                f"Audio transcribed: {result['text'][:50]}...",
                {
                    "audio_file": str(audio_path),
                    "text": result['text'],
                    "language": result['language'],
                    "duration": duration,
                    "processing_time": processing_time
                }
            )
            
            return {
                "text": result['text'],
                "language": result['language'],
                "confidence": 0.95,  # Mock confidence for real model
                "processing_time": processing_time,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            
            # Emit error event
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"Audio transcription failed: {e}",
                {"audio_file": str(audio_path)},
                EventSeverity.ERROR
            )
            
            # Return mock transcription as fallback
            return self._get_mock_transcription(audio_path)
    
    def _get_mock_transcription(self, audio_path: Path) -> Dict[str, Any]:
        """Get mock transcription for testing"""
        mock_text = f"This is a mock transcription of {audio_path.name}. In a real implementation, this would be the actual transcribed text from the audio file."
        
        return {
            "text": mock_text,
            "language": "en",
            "confidence": 0.85,
            "processing_time": 1.5,
            "duration": 10.0,
            "mock": True
        }
    
    async def transcribe_audio_bytes(self, audio_bytes: bytes) -> Dict[str, Any]:
        """Transcribe audio from bytes"""
        try:
            # Save temporary file
            temp_dir = Path("temp_audio")
            temp_dir.mkdir(exist_ok=True)
            temp_file = temp_dir / f"temp_{int(time.time())}.wav"
            
            # Write audio bytes to file
            with open(temp_file, "wb") as f:
                f.write(audio_bytes)
            
            # Transcribe
            result = await self.transcribe_audio(temp_file)
            
            # Clean up
            temp_file.unlink()
            
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio bytes: {e}")
            return self._get_mock_transcription(Path("mock"))
    
    async def transcribe_microphone(self, duration: float = 5.0) -> Dict[str, Any]:
        """Transcribe microphone input (placeholder implementation)"""
        try:
            # This would normally use PyAudio or similar to capture microphone input
            # For now, return mock transcription
            mock_text = "This is a mock transcription from microphone input. In a real implementation, this would capture audio from the microphone and transcribe it."
            
            await self.event_system.emit(
                EventType.AUDIO_CAPTURED,
                "Microphone audio captured",
                {"duration": duration}
            )
            
            return {
                "text": mock_text,
                "language": "en",
                "confidence": 0.90,
                "processing_time": 2.0,
                "duration": duration,
                "mock": True
            }
            
        except Exception as e:
            logger.error(f"Error transcribing microphone: {e}")
            return self._get_mock_transcription(Path("microphone"))
    
    async def get_available_models(self) -> list:
        """Get available Whisper models"""
        try:
            if not self._initialized:
                return ["base", "small", "medium", "large"]
            
            import whisper
            return whisper.available_models()
            
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return ["base", "small", "medium", "large"]
    
    async def change_model(self, model_name: str) -> bool:
        """Change the Whisper model"""
        try:
            if self._initialized:
                import whisper
                self.model = whisper.load_model(model_name)
                self.model_name = model_name
                
                logger.info(f"Changed Whisper model to: {model_name}")
                
                # Emit model changed event
                await self.event_system.emit(
                    EventType.MODEL_LOADED,
                    f"Whisper model changed to: {model_name}",
                    {"model_name": model_name}
                )
                
                return True
            else:
                logger.warning("Whisper not initialized, cannot change model")
                return False
                
        except Exception as e:
            logger.error(f"Error changing Whisper model: {e}")
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get current model information"""
        return {
            "model_name": self.model_name,
            "initialized": self._initialized,
            "device": "cpu",
            "available_models": await self.get_available_models()
        }
    
    async def transcribe_batch(self, audio_paths: list) -> list:
        """Transcribe multiple audio files"""
        results = []
        
        for audio_path in audio_paths:
            try:
                result = await self.transcribe_audio(Path(audio_path))
                results.append({
                    "file": audio_path,
                    "result": result
                })
            except Exception as e:
                logger.error(f"Error transcribing {audio_path}: {e}")
                results.append({
                    "file": audio_path,
                    "error": str(e)
                })
        
        return results
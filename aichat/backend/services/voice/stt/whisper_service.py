"""
Whisper service for speech-to-text functionality
"""

import logging
import time
from typing import Any, Dict, Optional
from pathlib import Path

import numpy as np
import soundfile as sf

# Third-party imports
try:
    import whisper
except ImportError:
    whisper = None

# Local imports
from aichat.constants.paths import TEMP_AUDIO_DIR, ensure_dirs
from aichat.core.event_system import EventSeverity, EventType, get_event_system
from aichat.backend.services.audio.audio_io_service import AudioIOService

logger = logging.getLogger(__name__)


class WhisperService:
    """Speech-to-text service using OpenAI Whisper"""
    
    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.model = None
        self._initialized = False
        self.event_system = get_event_system()
        self.audio_io = AudioIOService()
        
        # Initialize Whisper if available
        if whisper is not None:
            try:
                self.model = whisper.load_model(model_name)
                self._initialized = True
                logger.info(f"Whisper model '{model_name}' loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                self._initialized = False
        else:
            logger.error("Whisper not available - service cannot function")
            self._initialized = False
    
    
    async def transcribe_audio(self, audio_path: Path) -> Dict[str, Any]:
        """Transcribe audio file using Whisper"""
        try:
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            if not self._initialized:
                logger.error("Whisper not initialized - cannot transcribe audio")
                raise RuntimeError("Whisper service is not available")
            
            start_time = time.time()
            
            # Load and transcribe audio
            result = self.model.transcribe(str(audio_path))
            
            processing_time = time.time() - start_time
            
            # Emit transcription event
            await self.event_system.emit(
                EventType.AUDIO_TRANSCRIBED,
                f"Audio transcribed: {audio_path.name}",
                {
                    "file": str(audio_path),
                    "text": result["text"],
                    "language": result["language"],
                    "processing_time": processing_time
                }
            )
            
            return {
                "text": result["text"],
                "language": result["language"],
                "confidence": 0.95,  # Whisper doesn't provide confidence scores
                "processing_time": processing_time,
                "duration": result.get("duration", 0.0),
                "fallback": False,
            }
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise RuntimeError(f"Audio transcription failed: {e}")

    async def transcribe_audio_bytes(self, audio_bytes: bytes) -> Dict[str, Any]:
        """Transcribe audio from bytes"""
        try:
            # Save temporary file (centralized temp dir)
            temp_dir = TEMP_AUDIO_DIR
            ensure_dirs(temp_dir)
            temp_file = temp_dir / f"temp_{int(time.time())}.wav"

            # Write audio bytes to file
            with open(temp_file, "wb") as f:
                f.write(audio_bytes)

            # Transcribe
            result = await self.transcribe_audio(temp_file)

            # Clean up
            try:
                temp_file.unlink()
            except Exception:
                pass

            return result

        except Exception as e:
            logger.error(f"Error transcribing audio bytes: {e}")
            raise RuntimeError(f"Audio bytes transcription failed: {e}")

    async def transcribe_microphone(self, duration: float = 5.0) -> Dict[str, Any]:
        """Transcribe microphone input using AudioIOService"""
        try:
            # Record audio from microphone using AudioIOService
            audio_path = await self.audio_io.record_audio(duration)

            if audio_path and audio_path.exists():
                # Transcribe the recorded audio
                result = await self.transcribe_audio(audio_path)

                # Clean up temporary file
                try:
                    audio_path.unlink()
                except Exception:
                    pass

                return result
            else:
                # Fall back to fallback transcription if recording failed
                fallback_text = "[Audio recording unavailable] Microphone input could not be processed."

                await self.event_system.emit(
                    EventType.AUDIO_CAPTURED,
                    "Microphone audio captured (fallback)",
                    {"duration": duration},
                )

                return {
                    "text": fallback_text,
                    "language": "en",
                    "confidence": 0.90,
                    "processing_time": 2.0,
                    "duration": duration,
                    "fallback": True,
                }

        except Exception as e:
            logger.error(f"Error transcribing microphone: {e}")
            raise RuntimeError(f"Microphone transcription failed: {e}")

    async def get_available_models(self) -> list:
        """Get available Whisper models"""
        try:
            if not self._initialized:
                return ["base", "small", "medium", "large"]

            return whisper.available_models()

        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return ["base", "small", "medium", "large"]

    async def change_model(self, model_name: str) -> bool:
        """Change the Whisper model"""
        try:
            if self._initialized:

                self.model = whisper.load_model(model_name)
                self.model_name = model_name

                logger.info(f"Changed Whisper model to: {model_name}")

                # Emit model changed event
                await self.event_system.emit(
                    EventType.MODEL_LOADED,
                    f"Whisper model changed to: {model_name}",
                    {"model_name": model_name},
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
            "available_models": await self.get_available_models(),
        }

    async def transcribe_batch(self, audio_paths: list) -> list:
        """Transcribe multiple audio files"""
        results = []

        for audio_path in audio_paths:
            try:
                result = await self.transcribe_audio(Path(audio_path))
                results.append({"file": audio_path, "result": result})
            except Exception as e:
                logger.error(f"Error transcribing {audio_path}: {e}")
                results.append({"file": audio_path, "error": str(e)})

        return results
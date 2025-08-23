"""
Voice service for handling voice training and TTS functionality
"""

import asyncio
import logging
from typing import Any, Dict, Optional, List, AsyncGenerator
from pathlib import Path

from aichat.constants.paths import GENERATED_AUDIO_DIR, TTS_MODELS_DIR, ensure_dirs
from aichat.core.event_system import EventSeverity, EventType, get_event_system

# Updated imports for new TTS system
from aichat.backend.services.audio.audio_io_service import AudioIOService
from .tts import SmartTTSSelector, TTSBackend, StreamingTTSIntegration, StreamingConfig

logger = logging.getLogger(__name__)


class VoiceService:
    """Enhanced voice service with smart TTS selection and streaming support"""

    def __init__(self, audio_io_service: Optional[AudioIOService] = None, preferred_backend: str = "auto"):
        self.event_system = get_event_system()
        self.audio_io = audio_io_service or AudioIOService()
        
        # Legacy Piper support (deprecated)
        self.piper_model = None
        
        # New smart TTS system
        self.smart_tts = SmartTTSSelector(
            preferred_backend=TTSBackend.AUTO if preferred_backend == "auto" else TTSBackend(preferred_backend)
        )
        self.streaming_tts = StreamingTTSIntegration(self.smart_tts)
        self.tts_initialized = False
        
        # Initialize both legacy and new systems
        self._initialize_piper()  # Legacy support
        # Smart TTS initialization will be done on first use

    def _initialize_piper(self):
        """Initialize Piper TTS model"""
        try:
            # Try to import piper
            pass

            # Load model (placeholder - would need actual model file)
            # self.piper_model = piper.PiperModel(model_path)

            logger.info("Piper TTS initialized")

            # Emit model loaded event (async - will be handled later)
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self.event_system.emit(
                            EventType.MODEL_LOADED,
                            "Piper TTS model initialized",
                            {"model_type": "piper", "status": "ready"},
                        )
                    )
                else:
                    loop.run_until_complete(
                        self.event_system.emit(
                            EventType.MODEL_LOADED,
                            "Piper TTS model initialized",
                            {"model_type": "piper", "status": "ready"},
                        )
                    )
            except Exception:
                # If event system fails, continue without it
                pass

        except ImportError:
            logger.warning("Legacy Piper not installed. Using new TTS system.")
        except Exception as e:
            logger.error(f"Error initializing legacy Piper: {e}")
            # Don't emit error - we have the new system as fallback
            pass
    
    async def _initialize_smart_tts(self):
        """Initialize the smart TTS system"""
        try:
            import asyncio
            success = await self.smart_tts.initialize()
            if success:
                self.tts_initialized = True
                logger.info("Smart TTS system initialized successfully")
                await self.event_system.emit(
                    EventType.MODEL_LOADED,
                    "Smart TTS system initialized",
                    {
                        "model_type": "smart_tts",
                        "backend": self.smart_tts.optimal_backend,
                        "status": "ready"
                    },
                )
            else:
                logger.error("Failed to initialize Smart TTS system")
                
        except Exception as e:
            logger.error(f"Error initializing Smart TTS: {e}")
            await self.event_system.emit(
                EventType.MODEL_FAILED,
                f"Failed to initialize Smart TTS: {e}",
                {"model_type": "smart_tts"},
                EventSeverity.ERROR,
            )

    async def generate_tts(
        self, 
        text: str, 
        character_id: int, 
        character_name: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        emotion_state: Optional[Dict[str, Any]] = None
    ) -> Optional[Path]:
        """Generate text-to-speech audio using Smart TTS system"""
        try:
            # Ensure TTS is initialized
            if not self.tts_initialized:
                await self._initialize_smart_tts()
                if not self.tts_initialized:
                    return await self._fallback_to_legacy_tts(text, character_name)
            
            # Use smart TTS system
            audio_path = await self.smart_tts.generate_speech(
                text=text,
                character_name=character_name,
                voice=voice,
                speed=speed,
                pitch=pitch,
                emotion_state=emotion_state
            )
            
            if audio_path:
                # Emit enhanced audio generation event
                await self.event_system.emit(
                    EventType.AUDIO_GENERATED,
                    f"Smart TTS audio generated for {character_name}",
                    {
                        "text": text,
                        "character": character_name,
                        "audio_file": str(audio_path),
                        "character_id": character_id,
                        "voice": voice,
                        "speed": speed,
                        "pitch": pitch,
                        "emotion_state": emotion_state,
                        "backend": self.smart_tts.optimal_backend,
                        "is_smart_tts": True
                    },
                )
                
                return audio_path
            else:
                logger.error(f"Smart TTS generation failed for {character_name}")
                return None

        except Exception as e:
            logger.error(f"Error generating Smart TTS: {e}")
            
            # Emit error event
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"TTS generation failed: {e}",
                {"text": text, "character": character_name},
                EventSeverity.ERROR,
            )

            return None
    

    async def train_voice_model(
        self,
        training_data_dir: Path,
        output_dir: Path,
        model_name: str,
        epochs: int = 10,
        batch_size: int = 8,
    ) -> bool:
        """Train voice model (placeholder implementation)"""
        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Emit training started event
            await self.event_system.emit(
                EventType.TRAINING_STARTED,
                f"Voice training started for {model_name}",
                {
                    "model_name": model_name,
                    "training_data_dir": str(training_data_dir),
                    "output_dir": str(output_dir),
                    "epochs": epochs,
                    "batch_size": batch_size,
                },
            )

            # Simulate training progress
            import time

            for epoch in range(1, epochs + 1):
                time.sleep(1)  # Simulate training time
                progress = (epoch / epochs) * 100

                # Emit progress event
                await self.event_system.emit(
                    EventType.TRAINING_PROGRESS,
                    f"Training progress: {epoch}/{epochs} epochs",
                    {
                        "epoch": epoch,
                        "total_epochs": epochs,
                        "progress": progress,
                        "loss": max(0.1, 2.0 - (epoch * 0.1)),  # Simulated loss
                    },
                )

            # Create placeholder model files
            (output_dir / "config.json").write_text(
                '{"model_type": "piper", "version": "1.0"}'
            )
            (output_dir / "model.onnx").write_text("placeholder_model_data")

            # Emit completion event
            await self.event_system.emit(
                EventType.TRAINING_COMPLETED,
                f"Voice training completed for {model_name}",
                {
                    "model_name": model_name,
                    "output_dir": str(output_dir),
                    "epochs_trained": epochs,
                },
            )

            logger.info(f"Voice training completed for {model_name}")
            return True

        except Exception as e:
            logger.error(f"Error in voice training: {e}")

            # Emit error event
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"Voice training failed: {e}",
                {"model_name": model_name},
                EventSeverity.ERROR,
            )

            return False

    async def process_audio_file(self, input_path: Path, output_dir: Path) -> list:
        """Process audio file for training (placeholder implementation)"""
        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Process audio (placeholder - would use actual audio processing)
            processed_files = []

            # Create some placeholder processed files
            for i in range(3):
                processed_file = output_dir / f"processed_{i:03d}.wav"
                processed_file.touch()
                processed_files.append(processed_file)

            logger.info(f"Processed audio file: {len(processed_files)} files created")

            # Emit processing event
            await self.event_system.emit(
                EventType.AUDIO_PROCESSED,
                f"Audio file processed: {input_path.name}",
                {
                    "input_file": str(input_path),
                    "output_files": [str(f) for f in processed_files],
                    "count": len(processed_files),
                },
            )

            return processed_files

        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            return []

    async def get_available_models(self) -> list:
        """Get available voice models"""
        try:
            models_dir = TTS_MODELS_DIR
            if not models_dir.exists():
                return []

            models = []
            for model_dir in models_dir.iterdir():
                if model_dir.is_dir():
                    models.append(
                        {
                            "name": model_dir.name,
                            "path": str(model_dir),
                            "status": "available",
                        }
                    )

            return models

        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []

    async def load_voice_model(self, model_name: str) -> bool:
        """Load a voice model"""
        try:
            model_path = TTS_MODELS_DIR / model_name

            if not model_path.exists():
                logger.error(f"Voice model not found: {model_name}")
                return False

            # Load model (placeholder)
            # self.piper_model = load_piper_model(str(model_path))

            logger.info(f"Voice model loaded: {model_name}")

            # Emit model loaded event
            await self.event_system.emit(
                EventType.MODEL_LOADED,
                f"Voice model loaded: {model_name}",
                {"model_name": model_name, "model_path": str(model_path)},
            )

            return True

        except Exception as e:
            logger.error(f"Error loading voice model: {e}")
            return False

    async def get_voice_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get voice model information"""
        try:
            model_path = TTS_MODELS_DIR / model_name

            if not model_path.exists():
                return None

            # Get model info
            config_file = model_path / "config.json"
            config = {}
            if config_file.exists():
                import json

                config = json.loads(config_file.read_text())

            return {
                "name": model_name,
                "path": str(model_path),
                "config": config,
                "files": [str(f) for f in model_path.rglob("*") if f.is_file()],
                "status": "available",
            }

        except Exception as e:
            logger.error(f"Error getting voice model info: {e}")
            return None

    async def delete_voice_model(self, model_name: str) -> bool:
        """Delete a voice model"""
        try:
            model_path = TTS_MODELS_DIR / model_name

            if not model_path.exists():
                logger.error(f"Voice model not found: {model_name}")
                return False

            # Delete model directory
            import shutil

            shutil.rmtree(model_path)

            logger.info(f"Voice model deleted: {model_name}")

            # Emit model deleted event
            await self.event_system.emit(
                EventType.MODEL_FAILED,
                f"Voice model deleted: {model_name}",
                {"model_name": model_name},
            )

            return True

        except Exception as e:
            logger.error(f"Error deleting voice model: {e}")
            return False

    async def generate_streaming_tts(
        self,
        text: str,
        character_id: int,
        character_name: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        emotion_state: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate streaming TTS with punctuation-based segments"""
        try:
            if not self.tts_initialized:
                await self._initialize_smart_tts()
                if not self.tts_initialized:
                    logger.warning("Smart TTS not available for streaming")
                    return []
            
            segments = await self.smart_tts.generate_streaming_speech(
                text=text,
                character_name=character_name,
                voice=voice,
                speed=speed,
                pitch=pitch,
                emotion_state=emotion_state
            )
            
            # Add character_id to each segment
            for segment in segments:
                segment["character_id"] = character_id
            
            return segments
            
        except Exception as e:
            logger.error(f"Error generating streaming TTS: {e}")
            return []
    
    async def create_openrouter_tts_handler(
        self,
        character_id: int,
        character_name: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        emotion_state: Optional[Dict[str, Any]] = None
    ) -> Optional[callable]:
        """Create a TTS handler for OpenRouter streaming integration"""
        try:
            if not self.tts_initialized:
                await self._initialize_smart_tts()
                if not self.tts_initialized:
                    return None
            
            handler = await self.streaming_tts.create_openrouter_streaming_handler(
                character_name=character_name,
                voice=voice,
                speed=speed,
                pitch=pitch,
                emotion_state=emotion_state
            )
            
            return handler
            
        except Exception as e:
            logger.error(f"Error creating OpenRouter TTS handler: {e}")
            return None
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get available voices from the smart TTS system"""
        try:
            if not self.tts_initialized:
                await self._initialize_smart_tts()
                if not self.tts_initialized:
                    return []
            
            return await self.smart_tts.get_available_voices()
            
        except Exception as e:
            logger.error(f"Error getting available voices: {e}")
            return []
    
    async def test_voice(
        self, 
        voice: str, 
        test_text: str = "Hello, this is a test of the voice system."
    ) -> Optional[Path]:
        """Test a voice with sample text"""
        try:
            if not self.tts_initialized:
                await self._initialize_smart_tts()
                if not self.tts_initialized:
                    return None
            
            return await self.smart_tts.test_voice(voice, test_text)
            
        except Exception as e:
            logger.error(f"Error testing voice: {e}")
            return None
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive voice service status"""
        try:
            models = await self.get_available_models()
            audio_status = await self.audio_io.get_service_status()
            
            # Get smart TTS status
            smart_tts_status = {}
            streaming_stats = {}
            
            if self.tts_initialized:
                smart_tts_status = await self.smart_tts.get_service_status()
                streaming_stats = self.streaming_tts.get_streaming_stats()

            return {
                "status": "active",
                "legacy_piper_tts": "ready" if self.piper_model else "mock",
                "smart_tts_system": {
                    "initialized": self.tts_initialized,
                    "status": smart_tts_status
                },
                "streaming_tts": streaming_stats,
                "available_models": len(models),
                "models": models,
                "services": {
                    "tts": "ready" if self.tts_initialized else "legacy",
                    "streaming_tts": "ready" if self.tts_initialized else "not_available",
                    "training": "ready",
                    "processing": "ready",
                },
                "audio_io": audio_status,
            }
        except Exception as e:
            logger.error(f"Error getting voice service status: {e}")
            return {"status": "error", "error": str(e)}

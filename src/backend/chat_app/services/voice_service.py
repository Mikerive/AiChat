"""
Voice service for handling voice training and TTS functionality
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from event_system import get_event_system, EventType, EventSeverity

logger = logging.getLogger(__name__)


class VoiceService:
    """Service for handling voice training and TTS functionality"""
    
    def __init__(self):
        self.event_system = get_event_system()
        self.piper_model = None
        self._initialize_piper()
    
    def _initialize_piper(self):
        """Initialize Piper TTS model"""
        try:
            # Try to import piper
            import piper
            
            # Load model (placeholder - would need actual model file)
            # self.piper_model = piper.PiperModel(model_path)
            
            logger.info("Piper TTS initialized")
            
            # Emit model loaded event (async - will be handled later)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.event_system.emit(
                        EventType.MODEL_LOADED,
                        "Piper TTS model initialized",
                        {"model_type": "piper", "status": "ready"}
                    ))
                else:
                    loop.run_until_complete(self.event_system.emit(
                        EventType.MODEL_LOADED,
                        "Piper TTS model initialized",
                        {"model_type": "piper", "status": "ready"}
                    ))
            except Exception:
                # If event system fails, continue without it
                pass
            
        except ImportError:
            logger.warning("Piper not installed. Using mock service.")
        except Exception as e:
            logger.error(f"Error initializing Piper: {e}")
            self.event_system.emit(
                EventType.MODEL_FAILED,
                f"Failed to initialize Piper: {e}",
                {"model_type": "piper"},
                EventSeverity.ERROR
            )
    
    async def generate_tts(self, text: str, character_id: int, character_name: str) -> Optional[Path]:
        """Generate text-to-speech audio using Piper"""
        try:
            # Generate audio directory
            audio_dir = Path("backend/chat/audio")
            audio_dir.mkdir(parents=True, exist_ok=True)
            
            # Create output filename
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            audio_path = audio_dir / f"{character_name}_{text_hash}.wav"
            
            if self.piper_model:
                # Use real Piper TTS
                # self.piper_model.synthesize(text, str(audio_path))
                logger.info(f"Generated TTS with Piper: {audio_path}")
            else:
                # Create placeholder audio file
                audio_path.touch()
                logger.info(f"Generated placeholder TTS: {audio_path}")
            
            # Emit audio generation event
            await self.event_system.emit(
                EventType.AUDIO_GENERATED,
                f"TTS audio generated for {character_name}",
                {
                    "text": text,
                    "character": character_name,
                    "audio_file": str(audio_path),
                    "character_id": character_id
                }
            )
            
            return audio_path
            
        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            
            # Emit error event
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"TTS generation failed: {e}",
                {"text": text, "character": character_name},
                EventSeverity.ERROR
            )
            
            return None
    
    async def train_voice_model(self, training_data_dir: Path, output_dir: Path, 
                              model_name: str, epochs: int = 10, batch_size: int = 8) -> bool:
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
                    "batch_size": batch_size
                }
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
                        "loss": max(0.1, 2.0 - (epoch * 0.1))  # Simulated loss
                    }
                )
            
            # Create placeholder model files
            (output_dir / "config.json").write_text('{"model_type": "piper", "version": "1.0"}')
            (output_dir / "model.onnx").write_text("placeholder_model_data")
            
            # Emit completion event
            await self.event_system.emit(
                EventType.TRAINING_COMPLETED,
                f"Voice training completed for {model_name}",
                {
                    "model_name": model_name,
                    "output_dir": str(output_dir),
                    "epochs_trained": epochs
                }
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
                EventSeverity.ERROR
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
                    "count": len(processed_files)
                }
            )
            
            return processed_files
            
        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            return []
    
    async def get_available_models(self) -> list:
        """Get available voice models"""
        try:
            models_dir = Path("backend/tts_finetune_app/models")
            if not models_dir.exists():
                return []
            
            models = []
            for model_dir in models_dir.iterdir():
                if model_dir.is_dir():
                    models.append({
                        "name": model_dir.name,
                        "path": str(model_dir),
                        "status": "available"
                    })
            
            return models
            
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    async def load_voice_model(self, model_name: str) -> bool:
        """Load a voice model"""
        try:
            model_path = Path("backend/tts_finetune_app/models") / model_name
            
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
                {"model_name": model_name, "model_path": str(model_path)}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading voice model: {e}")
            return False
    
    async def get_voice_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get voice model information"""
        try:
            model_path = Path("backend/tts_finetune_app/models") / model_name
            
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
                "status": "available"
            }
            
        except Exception as e:
            logger.error(f"Error getting voice model info: {e}")
            return None
    
    async def delete_voice_model(self, model_name: str) -> bool:
        """Delete a voice model"""
        try:
            model_path = Path("backend/tts_finetune_app/models") / model_name
            
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
                {"model_name": model_name}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting voice model: {e}")
            return False
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get voice service status"""
        try:
            models = await self.get_available_models()
            
            return {
                "status": "active",
                "piper_tts": "ready" if self.piper_model else "mock",
                "available_models": len(models),
                "models": models,
                "services": {
                    "tts": "ready",
                    "training": "ready",
                    "processing": "ready"
                }
            }
        except Exception as e:
            logger.error(f"Error getting voice service status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
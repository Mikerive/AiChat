"""
Piper TTS Service for high-quality text-to-speech generation
"""

import logging
import asyncio
import subprocess
import tempfile
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants.paths import PIPER_MODELS, AUDIO_OUTPUT, ensure_dirs

from event_system import get_event_system, EventType, EventSeverity

logger = logging.getLogger(__name__)


class PiperTTSService:
    """Service for generating speech using Piper TTS"""
    
    def __init__(self):
        self.event_system = get_event_system()
        self.models_path = PIPER_MODELS
        self.output_path = AUDIO_OUTPUT
        self.piper_executable = self._find_piper_executable()
        self.default_voice = "en_US-hfc_female-medium"
        self.available_voices = {}
        self._initialize_directories()
    
    def _initialize_directories(self):
        """Initialize required directories"""
        ensure_dirs(self.models_path, self.output_path)
    
    def _find_piper_executable(self) -> Optional[str]:
        """Find Piper executable in system"""
        possible_paths = [
            "piper",
            "piper.exe",
            "./piper",
            "./piper.exe",
            "/usr/local/bin/piper",
            "/usr/bin/piper",
            str(Path.home() / ".local/bin/piper"),
            "C:\\Program Files\\Piper\\piper.exe",
            "C:\\piper\\piper.exe"
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    logger.info(f"Found Piper executable at: {path}")
                    return path
            except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        logger.warning("Piper executable not found. TTS will use fallback mode.")
        return None
    
    async def generate_speech(
        self,
        text: str,
        character_name: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        noise_scale: float = 0.667,
        length_scale: float = 1.0
    ) -> Optional[Path]:
        """Generate speech audio from text"""
        try:
            # Emit processing start event
            await self.event_system.emit(
                EventType.AUDIO_GENERATED,
                f"Starting TTS generation for {character_name}",
                {
                    "character": character_name,
                    "text_length": len(text),
                    "voice": voice or self.default_voice,
                    "speed": speed
                }
            )
            
            if not self.piper_executable:
                logger.warning("Piper not available, creating placeholder audio file")
                return await self._create_placeholder_audio(text, character_name)
            
            # Select voice for character
            selected_voice = await self._select_voice_for_character(character_name, voice)
            
            # Check if voice model exists
            model_path = await self._ensure_voice_model(selected_voice)
            if not model_path:
                logger.warning(f"Voice model not found: {selected_voice}, using placeholder")
                return await self._create_placeholder_audio(text, character_name)
            
            # Generate unique filename
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            output_filename = f"{character_name}_{text_hash}_{selected_voice}.wav"
            output_path = self.output_path / output_filename
            
            # Run Piper TTS
            success = await self._run_piper_tts(
                text=text,
                model_path=model_path,
                output_path=output_path,
                speed=speed,
                noise_scale=noise_scale,
                length_scale=length_scale
            )
            
            if success and output_path.exists():
                # Emit success event
                await self.event_system.emit(
                    EventType.AUDIO_GENERATED,
                    f"TTS audio generated successfully for {character_name}",
                    {
                        "character": character_name,
                        "voice": selected_voice,
                        "output_file": str(output_path),
                        "file_size": output_path.stat().st_size,
                        "text_length": len(text)
                    }
                )
                
                return output_path
            else:
                logger.error("TTS generation failed, creating placeholder")
                return await self._create_placeholder_audio(text, character_name)
            
        except Exception as e:
            logger.error(f"Error in TTS generation: {e}")
            
            # Emit error event
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"TTS generation error: {str(e)}",
                {"character": character_name, "text": text[:100], "error": str(e)},
                EventSeverity.ERROR
            )
            
            # Return placeholder
            return await self._create_placeholder_audio(text, character_name)
    
    async def _select_voice_for_character(self, character_name: str, requested_voice: Optional[str]) -> str:
        """Select appropriate voice for character"""
        if requested_voice:
            return requested_voice
        
        # Character-specific voice mapping
        character_voices = {
            "hatsune_miku": "en_US-amy-medium",  # Higher pitched female voice
            "default": self.default_voice
        }
        
        character_key = character_name.lower()
        return character_voices.get(character_key, character_voices["default"])
    
    async def _ensure_voice_model(self, voice: str) -> Optional[Path]:
        """Ensure voice model is available"""
        model_file = self.models_path / f"{voice}.onnx"
        config_file = self.models_path / f"{voice}.onnx.json"
        
        if model_file.exists() and config_file.exists():
            return model_file
        
        # In a real implementation, this would download the model
        logger.warning(f"Voice model not found: {voice}")
        logger.info("To use Piper TTS, download voice models from: https://github.com/rhasspy/piper/releases")
        
        return None
    
    async def _run_piper_tts(
        self,
        text: str,
        model_path: Path,
        output_path: Path,
        speed: float = 1.0,
        noise_scale: float = 0.667,
        length_scale: float = 1.0
    ) -> bool:
        """Run Piper TTS subprocess"""
        try:
            # Prepare command
            cmd = [
                self.piper_executable,
                "--model", str(model_path),
                "--output_file", str(output_path),
                "--speaker", "0",
                "--noise_scale", str(noise_scale),
                "--length_scale", str(length_scale)
            ]
            
            # Run subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send text to stdin
            stdout, stderr = await process.communicate(text.encode())
            
            if process.returncode == 0:
                logger.info(f"Piper TTS completed successfully: {output_path}")
                return True
            else:
                logger.error(f"Piper TTS failed with return code {process.returncode}")
                logger.error(f"Stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error running Piper TTS: {e}")
            return False
    
    async def _create_placeholder_audio(self, text: str, character_name: str) -> Path:
        """Create placeholder audio file when Piper is not available"""
        try:
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            output_filename = f"{character_name}_{text_hash}_placeholder.wav"
            output_path = self.output_path / output_filename
            
            # Create a minimal WAV file (silent audio)
            # WAV header for 1 second of silence at 22050Hz, 16-bit mono
            wav_header = bytes([
                0x52, 0x49, 0x46, 0x46,  # "RIFF"
                0x2C, 0xAC, 0x00, 0x00,  # File size (44100 + 36)
                0x57, 0x41, 0x56, 0x45,  # "WAVE"
                0x66, 0x6D, 0x74, 0x20,  # "fmt "
                0x10, 0x00, 0x00, 0x00,  # Subchunk1Size (16)
                0x01, 0x00,              # AudioFormat (PCM)
                0x01, 0x00,              # NumChannels (1)
                0x22, 0x56, 0x00, 0x00,  # SampleRate (22050)
                0x44, 0xAC, 0x00, 0x00,  # ByteRate (44100)
                0x02, 0x00,              # BlockAlign (2)
                0x10, 0x00,              # BitsPerSample (16)
                0x64, 0x61, 0x74, 0x61,  # "data"
                0x00, 0xAC, 0x00, 0x00   # Subchunk2Size (44100)
            ])
            
            with open(output_path, 'wb') as f:
                f.write(wav_header)
                # Write 1 second of silence (44100 bytes of zeros)
                f.write(b'\x00' * 44100)
            
            logger.info(f"Created placeholder audio file: {output_path}")
            
            # Emit placeholder event
            await self.event_system.emit(
                EventType.AUDIO_GENERATED,
                f"Placeholder audio created for {character_name}",
                {
                    "character": character_name,
                    "voice": "placeholder",
                    "output_file": str(output_path),
                    "is_placeholder": True
                }
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating placeholder audio: {e}")
            raise
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices"""
        try:
            voices = []
            
            # Scan for available voice models
            for model_file in self.models_path.glob("*.onnx"):
                voice_name = model_file.stem
                config_file = model_file.with_suffix(".onnx.json")
                
                voice_info = {
                    "name": voice_name,
                    "model_file": str(model_file),
                    "config_available": config_file.exists()
                }
                
                # Try to read config for additional info
                if config_file.exists():
                    try:
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                            voice_info.update({
                                "language": config.get("language", "unknown"),
                                "dataset": config.get("dataset", "unknown"),
                                "quality": config.get("quality", "unknown")
                            })
                    except Exception as e:
                        logger.warning(f"Error reading config for {voice_name}: {e}")
                
                voices.append(voice_info)
            
            return voices
            
        except Exception as e:
            logger.error(f"Error getting available voices: {e}")
            return []
    
    async def download_voice_model(self, voice_name: str, url: str) -> bool:
        """Download a voice model (placeholder implementation)"""
        try:
            logger.info(f"Voice model download not implemented. Please manually download {voice_name} from {url}")
            logger.info(f"Place voice files in: {self.models_path}")
            return False
            
        except Exception as e:
            logger.error(f"Error downloading voice model: {e}")
            return False
    
    async def test_voice(self, voice: str, test_text: str = "Hello, this is a test.") -> Optional[Path]:
        """Test a voice with sample text"""
        try:
            return await self.generate_speech(
                text=test_text,
                character_name="test",
                voice=voice
            )
            
        except Exception as e:
            logger.error(f"Error testing voice {voice}: {e}")
            return None
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get TTS service status"""
        try:
            available_voices = await self.get_available_voices()
            
            return {
                "piper_available": self.piper_executable is not None,
                "piper_path": self.piper_executable,
                "models_path": str(self.models_path),
                "output_path": str(self.output_path),
                "available_voices": len(available_voices),
                "default_voice": self.default_voice,
                "status": "ready" if self.piper_executable else "fallback_mode"
            }
            
        except Exception as e:
            logger.error(f"Error getting TTS service status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
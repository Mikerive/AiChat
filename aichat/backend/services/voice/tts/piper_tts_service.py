"""
Piper TTS Service for high-quality text-to-speech generation
"""

import asyncio
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional
from pathlib import Path

# Local imports
from aichat.constants.paths import AUDIO_OUTPUT, PIPER_MODELS, ensure_dirs
from aichat.core.event_system import EventSeverity, EventType, get_event_system
from ..io_services.audio_io_service import AudioIOService

            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            output_filename = f"{character_name}_{text_hash}_placeholder.wav"
            output_path = self.output_path / output_filename

            # Create a minimal WAV file (silent audio)
            # WAV header for 1 second of silence at 22050Hz, 16-bit mono
            wav_header = bytes(
                [
                    0x52,
                    0x49,
                    0x46,
                    0x46,  # "RIFF"
                    0x2C,
                    0xAC,
                    0x00,
                    0x00,  # File size (44100 + 36)
                    0x57,
                    0x41,
                    0x56,
                    0x45,  # "WAVE"
                    0x66,
                    0x6D,
                    0x74,
                    0x20,  # "fmt "
                    0x10,
                    0x00,
                    0x00,
                    0x00,  # Subchunk1Size (16)
                    0x01,
                    0x00,  # AudioFormat (PCM)
                    0x01,
                    0x00,  # NumChannels (1)
                    0x22,
                    0x56,
                    0x00,
                    0x00,  # SampleRate (22050)
                    0x44,
                    0xAC,
                    0x00,
                    0x00,  # ByteRate (44100)
                    0x02,
                    0x00,  # BlockAlign (2)
                    0x10,
                    0x00,  # BitsPerSample (16)
                    0x64,
                    0x61,
                    0x74,
                    0x61,  # "data"
                    0x00,
                    0xAC,
                    0x00,
                    0x00,  # Subchunk2Size (44100)
                ]
            )

            with open(output_path, "wb") as f:
                f.write(wav_header)
                # Write 1 second of silence (44100 bytes of zeros)
                f.write(b"\x00" * 44100)

            logger.info(f"Created placeholder audio file: {output_path}")

            # Emit placeholder event
            await self.event_system.emit(
                EventType.AUDIO_GENERATED,
                f"Placeholder audio created for {character_name}",
                {
                    "character": character_name,
                    "voice": "placeholder",
                    "output_file": str(output_path),
                    "is_placeholder": True,
                },
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
                    "config_available": config_file.exists(),
                }

                # Try to read config for additional info
                if config_file.exists():
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            voice_info.update(
                                {
                                    "language": config.get("language", "unknown"),
                                    "dataset": config.get("dataset", "unknown"),
                                    "quality": config.get("quality", "unknown"),
                                }
                            )
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
            logger.info(
                f"Voice model download not implemented. Please manually download {voice_name} from {url}"
            )
            logger.info(f"Place voice files in: {self.models_path}")
            return False

        except Exception as e:
            logger.error(f"Error downloading voice model: {e}")
            return False

    async def test_voice(
        self, voice: str, test_text: str = "Hello, this is a test."
    ) -> Optional[Path]:
        """Test a voice with sample text"""
        try:
            return await self.generate_speech(
                text=test_text, character_name="test", voice=voice
            )

        except Exception as e:
            logger.error(f"Error testing voice {voice}: {e}")
            return None

    async def play_generated_audio(self, audio_path: Path) -> bool:
        """Play generated audio using AudioIOService"""
        try:
            if not audio_path or not audio_path.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return False

            return await self.audio_io.play_audio(audio_path)

        except Exception as e:
            logger.error(f"Error playing generated audio: {e}")
            return False

    async def get_service_status(self) -> Dict[str, Any]:
        """Get TTS service status"""
        try:
            available_voices = await self.get_available_voices()
            audio_status = await self.audio_io.get_service_status()

            return {
                "piper_available": self.piper_executable is not None,
                "piper_path": self.piper_executable,
                "models_path": str(self.models_path),
                "output_path": str(self.output_path),
                "available_voices": len(available_voices),
                "default_voice": self.default_voice,
                "status": "ready" if self.piper_executable else "fallback_mode",
                "audio_io": audio_status,
            }

        except Exception as e:
            logger.error(f"Error getting TTS service status: {e}")
            return {"status": "error", "error": str(e)}

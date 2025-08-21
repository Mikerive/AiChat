"""
Chat service for handling character conversations
"""

import logging
from typing import Any, Dict, Optional

# Local imports
from aichat.constants.paths import AUDIO_OUTPUT, ensure_dirs
from aichat.core.database import Character, db_ops
from aichat.core.event_system import EventSeverity, EventType, get_event_system
            from .openrouter_service import OpenRouterService
            from .piper_tts_service import PiperTTSService

                text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                audio_path = audio_dir / f"{character_name}_{text_hash}_fallback.wav"

                # Create minimal WAV file
                wav_header = bytes(
                    [
                        0x52,
                        0x49,
                        0x46,
                        0x46,  # "RIFF"
                        0x2C,
                        0xAC,
                        0x00,
                        0x00,  # File size
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
                        0x00,  # Subchunk1Size
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
                        0x00,  # ByteRate
                        0x02,
                        0x00,  # BlockAlign
                        0x10,
                        0x00,  # BitsPerSample
                        0x64,
                        0x61,
                        0x74,
                        0x61,  # "data"
                        0x00,
                        0xAC,
                        0x00,
                        0x00,  # Subchunk2Size
                    ]
                )

                with open(audio_path, "wb") as f:
                    f.write(wav_header)
                    f.write(b"\x00" * 44100)  # 1 second of silence

                logger.info(f"Created fallback TTS audio: {audio_path}")
                return audio_path

            except Exception as fallback_error:
                logger.error(f"Error creating fallback TTS: {fallback_error}")
                return None

    async def get_chat_status(self) -> Dict[str, Any]:
        """Get chat system status"""
        try:
            return {
                "status": "active",
                "current_character": self.current_character,
                "characters_count": len(await self.list_characters()),
                "services": {"chat": "ready", "tts": "ready", "llm": "ready"},
            }
        except Exception as e:
            logger.error(f"Error getting chat status: {e}")
            return {"status": "error", "error": str(e)}

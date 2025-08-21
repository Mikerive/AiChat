"""
Discord service configuration
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class AudioQuality(Enum):
    """Audio quality settings"""

    LOW = "low"  # 8kHz, 16-bit
    MEDIUM = "medium"  # 16kHz, 16-bit
    HIGH = "high"  # 48kHz, 16-bit


class VADSensitivity(Enum):
    """Voice Activity Detection sensitivity levels"""

    LOW = 0  # Less sensitive, fewer false positives
    MEDIUM = 1  # Balanced
    HIGH = 2  # More sensitive, catches quiet speech


@dataclass
class DiscordConfig:
    """Discord service configuration"""

    # Bot authentication
    bot_token: Optional[str] = None

    # Server/channel targeting
    guild_id: Optional[int] = None
    voice_channel_id: Optional[int] = None
    text_channel_id: Optional[int] = None

    # Connection behavior
    auto_join_voice: bool = True
    auto_reconnect: bool = True
    reconnect_delay: float = 5.0

    # Audio capture settings
    record_audio: bool = True
    audio_quality: AudioQuality = AudioQuality.MEDIUM
    sample_rate: int = 16000
    channels: int = 1
    frame_size: int = 960  # 20ms at 48kHz

    # Voice Activity Detection
    enable_vad: bool = True
    vad_sensitivity: VADSensitivity = VADSensitivity.MEDIUM
    vad_min_duration: float = 0.3  # Minimum speech duration in seconds
    vad_silence_timeout: float = 1.0  # Silence timeout before ending speech

    # Audio processing
    enable_noise_suppression: bool = True
    enable_auto_gain: bool = True
    audio_buffer_size: int = 10  # Seconds of audio to buffer

    # User tracking
    track_speaking: bool = True
    track_presence: bool = True
    allowed_users: Optional[List[int]] = None  # If set, only track these user IDs
    ignore_bots: bool = True

    # Transcription integration
    enable_transcription: bool = True
    transcription_service: str = "whisper"  # "whisper" or custom
    transcription_language: Optional[str] = None  # Auto-detect if None

    # Privacy and consent
    require_user_consent: bool = True
    consent_timeout: float = 30.0  # Seconds to wait for consent

    # Performance
    max_concurrent_transcriptions: int = 3
    cleanup_old_audio: bool = True
    max_audio_age: float = 3600.0  # Seconds to keep old audio files

    # Debugging
    debug_audio: bool = False
    save_raw_audio: bool = False
    log_voice_events: bool = True

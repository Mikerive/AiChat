"""
Discord Service Constants

Pure data model for Discord bot configuration - no business logic.
"""

from enum import Enum
from pydantic import BaseModel, Field, computed_field


class AudioQuality(Enum):
    """Audio quality settings"""
    LOW = "low"      # 8kHz, 16-bit
    MEDIUM = "medium"  # 16kHz, 16-bit
    HIGH = "high"    # 48kHz, 16-bit


class VADSensitivity(Enum):
    """Voice Activity Detection sensitivity levels"""
    LOW = 0      # Less sensitive, fewer false positives
    MEDIUM = 1   # Balanced
    HIGH = 2     # More sensitive, catches quiet speech


class DiscordConstants(BaseModel):
    """Discord service configuration - pure data model"""
    
    # Connection Behavior
    auto_join_voice: bool = Field(default=True, description="Auto-join voice channels")
    auto_reconnect: bool = Field(default=True, description="Auto-reconnect on disconnect")
    reconnect_delay: float = Field(default=5.0, ge=1.0, le=60.0, description="Reconnect delay in seconds")
    connection_timeout: float = Field(default=30.0, ge=5.0, le=120.0, description="Connection timeout")
    
    # Audio Capture
    record_audio: bool = Field(default=True, description="Enable audio recording")
    audio_quality: AudioQuality = Field(default=AudioQuality.MEDIUM)
    
    # Audio Processing Parameters
    sample_rate: int = Field(default=16000, description="Processing sample rate")
    channels: int = Field(default=1, ge=1, le=2, description="Processing channels")
    frame_size: int = Field(default=960, description="Frame size (20ms at 48kHz)")
    native_sample_rate: int = Field(default=48000, description="Discord's actual rate")
    native_channels: int = Field(default=2, description="Discord supports stereo")
    
    # Voice Activity Detection
    enable_vad: bool = Field(default=True, description="Enable VAD")
    vad_sensitivity: VADSensitivity = Field(default=VADSensitivity.MEDIUM)
    vad_min_duration: float = Field(default=0.3, ge=0.1, le=5.0, description="Min speech duration")
    vad_silence_timeout: float = Field(default=1.0, ge=0.1, le=10.0, description="Silence timeout")
    
    # Audio Enhancement
    enable_noise_suppression: bool = Field(default=True, description="Enable noise suppression")
    enable_auto_gain: bool = Field(default=True, description="Enable auto gain control")
    audio_buffer_size: int = Field(default=10, ge=1, le=60, description="Audio buffer size in seconds")
    
    # User Tracking
    track_speaking: bool = Field(default=True, description="Track speaking events")
    track_presence: bool = Field(default=True, description="Track presence changes")
    ignore_bots: bool = Field(default=True, description="Ignore bot audio")
    
    # Transcription
    enable_transcription: bool = Field(default=True, description="Enable transcription")
    transcription_service: str = Field(default="whisper", description="Transcription service")
    transcription_language: str = Field(default=None, description="Language for transcription")
    
    # Privacy
    require_user_consent: bool = Field(default=True, description="Require user consent")
    consent_timeout: float = Field(default=30.0, ge=5.0, le=300.0, description="Consent timeout")
    
    # Performance
    max_concurrent_transcriptions: int = Field(default=3, ge=1, le=20, description="Max concurrent transcriptions")
    cleanup_old_audio: bool = Field(default=True, description="Cleanup old audio files")
    max_audio_age: float = Field(default=3600.0, ge=60.0, le=86400.0, description="Max audio age in seconds")
    
    # Debugging
    debug_audio: bool = Field(default=False, description="Enable audio debugging")
    save_raw_audio: bool = Field(default=False, description="Save raw audio files")
    log_voice_events: bool = Field(default=True, description="Log voice events")
    
    # Rate Limiting
    message_rate_limit: float = Field(default=1.0, ge=0.1, le=10.0, description="Message rate limit")
    command_cooldown: float = Field(default=2.0, ge=0.1, le=30.0, description="Command cooldown")
    
    # Error Handling
    max_reconnect_attempts: int = Field(default=5, ge=1, le=20, description="Max reconnect attempts")
    error_retry_delay: float = Field(default=2.0, ge=0.5, le=60.0, description="Error retry delay")
    
    @computed_field
    @property
    def processing_sample_rate(self) -> int:
        """Sample rate used for audio processing"""
        quality_rates = {
            AudioQuality.LOW: 8000,
            AudioQuality.MEDIUM: 16000,
            AudioQuality.HIGH: 48000
        }
        return quality_rates.get(self.audio_quality, self.sample_rate)
    
    @computed_field
    @property
    def frame_duration_ms(self) -> float:
        """Frame duration in milliseconds"""
        return (self.frame_size * 1000) / self.native_sample_rate
    
    class Config:
        use_enum_values = True
        extra = "ignore"
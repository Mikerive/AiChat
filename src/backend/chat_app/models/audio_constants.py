"""
Audio Processing Constants

Pure data model for audio configuration - no business logic.
"""

from enum import Enum
from pydantic import BaseModel, Field, validator, computed_field


class AudioQuality(Enum):
    """Audio quality presets"""
    LOW = "low"          # 8kHz, 16-bit
    MEDIUM = "medium"    # 16kHz, 16-bit  
    HIGH = "high"        # 48kHz, 16-bit


class AudioFormat(Enum):
    """Supported audio formats"""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"


class AudioConstants(BaseModel):
    """Audio processing configuration - pure data model"""
    
    # Core Settings
    sample_rate: int = Field(default=16000, description="Sample rate in Hz")
    channels: int = Field(default=1, ge=1, le=2, description="Number of audio channels")
    bit_depth: int = Field(default=16, description="Bits per sample")
    quality_preset: AudioQuality = Field(default=AudioQuality.MEDIUM)
    
    # Frame Processing
    frame_size_ms: int = Field(default=20, description="Frame duration in milliseconds")
    
    # Enhancement Settings
    enable_noise_suppression: bool = Field(default=True, description="Basic noise reduction")
    enable_auto_gain_control: bool = Field(default=True, description="Automatic gain control")
    
    # File Settings
    output_format: AudioFormat = Field(default=AudioFormat.WAV)
    temp_file_cleanup: bool = Field(default=True, description="Auto-cleanup temporary files")
    
    # Buffer Settings
    input_buffer_duration_s: float = Field(default=5.0, ge=0.5, le=30.0, description="Input buffer duration")
    max_buffer_memory_mb: int = Field(default=100, ge=10, le=1000, description="Maximum buffer memory usage")
    
    # Service-Specific Sample Rates (reference only)
    discord_sample_rate: int = Field(default=48000, description="Discord's native sample rate")
    discord_frame_size: int = Field(default=960, description="Discord frame size")
    discord_channels: int = Field(default=2, ge=1, le=2, description="Discord supports stereo")
    
    transcription_sample_rate: int = Field(default=16000, description="Optimal rate for STT models")
    tts_sample_rate: int = Field(default=22050, description="Common TTS output rate")
    tts_channels: int = Field(default=1, ge=1, le=2, description="TTS channels")
    
    @validator('bit_depth')
    def validate_bit_depth(cls, v):
        """Validate bit depth is supported"""
        if v not in [16, 24]:
            raise ValueError(f"Bit depth must be 16 or 24, got {v}")
        return v
    
    @computed_field
    @property
    def effective_sample_rate(self) -> int:
        """Effective sample rate based on quality preset"""
        preset_rates = {
            AudioQuality.LOW: 8000,
            AudioQuality.MEDIUM: 16000,
            AudioQuality.HIGH: 48000
        }
        return preset_rates.get(self.quality_preset, self.sample_rate)
    
    @computed_field
    @property 
    def frame_size_samples(self) -> int:
        """Frame size in samples"""
        return int(self.effective_sample_rate * self.frame_size_ms / 1000)
    
    @computed_field
    @property
    def bytes_per_frame(self) -> int:
        """Bytes per audio frame"""
        return self.frame_size_samples * self.channels * (self.bit_depth // 8)
    
    class Config:
        use_enum_values = True
        extra = "ignore"
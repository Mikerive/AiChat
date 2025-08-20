"""
Voice Activity Detection Constants

Pure data model with validation - no business logic.
"""

from enum import Enum
from pydantic import BaseModel, Field, validator, computed_field


class VADSensitivityPreset(Enum):
    """VAD sensitivity levels"""
    LOW = "low"              # Conservative detection
    MEDIUM = "medium"        # Balanced (default)
    HIGH = "high"            # Sensitive detection


class VADConstants(BaseModel):
    """Voice Activity Detection configuration - pure data model"""
    
    # WebRTC VAD Settings
    webrtc_aggressiveness: int = Field(default=2, ge=0, le=3, description="WebRTC aggressiveness (0-3)")
    webrtc_frame_duration_ms: int = Field(default=20, description="Frame duration in ms")
    
    # Energy Fallback
    energy_threshold_db: float = Field(default=-40.0, ge=-80.0, le=-10.0, description="Energy threshold in dB")
    
    # Timing
    min_speech_duration_ms: int = Field(default=300, ge=50, le=5000, description="Minimum speech duration")
    max_silence_duration_ms: int = Field(default=1000, ge=100, le=10000, description="Maximum silence duration")
    
    # Settings
    sensitivity_preset: VADSensitivityPreset = Field(default=VADSensitivityPreset.MEDIUM)
    save_speech_segments: bool = Field(default=True, description="Save detected speech segments")
    max_concurrent_sources: int = Field(default=50, ge=1, le=200, description="Maximum audio sources to track")
    
    @validator('webrtc_frame_duration_ms')
    def validate_frame_duration(cls, v):
        """Validate WebRTC frame duration is supported"""
        if v not in [10, 20, 30]:
            raise ValueError(f"WebRTC frame duration must be 10, 20, or 30ms, got {v}")
        return v
    
    @validator('max_silence_duration_ms')
    def validate_silence_greater_than_speech(cls, v, values):
        """Validate max silence is greater than min speech duration"""
        if 'min_speech_duration_ms' in values and v <= values['min_speech_duration_ms']:
            raise ValueError("Max silence duration must be greater than min speech duration")
        return v
    
    @computed_field
    @property
    def effective_energy_threshold_db(self) -> float:
        """Computed energy threshold based on sensitivity preset"""
        preset_thresholds = {
            VADSensitivityPreset.LOW: -35.0,
            VADSensitivityPreset.MEDIUM: -40.0,
            VADSensitivityPreset.HIGH: -45.0
        }
        return preset_thresholds.get(self.sensitivity_preset, self.energy_threshold_db)
    
    @computed_field
    @property
    def effective_webrtc_aggressiveness(self) -> int:
        """Computed WebRTC aggressiveness based on sensitivity preset"""
        preset_mapping = {
            VADSensitivityPreset.LOW: 1,
            VADSensitivityPreset.MEDIUM: 2,
            VADSensitivityPreset.HIGH: 3
        }
        return preset_mapping.get(self.sensitivity_preset, self.webrtc_aggressiveness)
    
    @computed_field
    @property
    def min_speech_duration_s(self) -> float:
        """Minimum speech duration in seconds"""
        return self.min_speech_duration_ms / 1000.0
    
    @computed_field
    @property
    def max_silence_duration_s(self) -> float:
        """Maximum silence duration in seconds"""
        return self.max_silence_duration_ms / 1000.0
    
    class Config:
        use_enum_values = True
        extra = "ignore"
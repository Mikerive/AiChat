"""
Text-to-Speech Constants

Pure data model for TTS configuration - no business logic.
"""

from typing import Dict
from pydantic import BaseModel, Field, validator


class TTSConstants(BaseModel):
    """Text-to-Speech configuration - pure data model"""
    
    # Piper TTS Quality Parameters
    speed: float = Field(default=1.0, ge=0.1, le=3.0, description="Speech rate")
    noise_scale: float = Field(default=0.667, ge=0.0, le=1.0, description="Audio quality vs naturalness")
    length_scale: float = Field(default=1.0, ge=0.1, le=3.0, description="Phoneme duration")
    
    # Voice Configuration
    default_voice: str = Field(default="en_US-amy-medium", description="Default Piper voice model")
    character_voices: Dict[str, str] = Field(
        default_factory=lambda: {
            "miku": "en_US-amy-medium",
            "amy": "en_US-amy-medium", 
            "default": "en_US-amy-medium"
        },
        description="Character to voice model mapping"
    )
    
    # Output Settings
    output_sample_rate: int = Field(default=22050, ge=8000, le=48000, description="Output sample rate")
    output_channels: int = Field(default=1, ge=1, le=2, description="Output channels")
    output_format: str = Field(default="wav", pattern=r"^(wav|mp3|flac)$", description="Output format")
    
    # Performance Limits
    max_concurrent_generations: int = Field(default=3, ge=1, le=20, description="Max concurrent TTS requests")
    generation_timeout: float = Field(default=30.0, ge=5.0, le=300.0, description="Generation timeout (seconds)")
    
    @validator('speed')
    def speed_performance_warning(cls, v):
        """Log warning for extreme speed values (doesn't fail validation)"""
        if v < 0.5 or v > 2.0:
            # Service layer should handle warnings
            pass
        return v
    
    class Config:
        use_enum_values = True
        extra = "ignore"
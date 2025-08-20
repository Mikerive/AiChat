"""
Speech-to-Text Constants

Pure data model for STT configuration - no business logic.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, validator, computed_field


class WhisperModel(Enum):
    """Available Whisper model sizes"""
    TINY = "tiny"           # ~39 MB, fastest
    BASE = "base"           # ~74 MB, good balance  
    SMALL = "small"         # ~244 MB, better accuracy
    MEDIUM = "medium"       # ~769 MB, high accuracy
    LARGE = "large"         # ~1550 MB, best accuracy


class STTConstants(BaseModel):
    """Speech-to-Text configuration - pure data model"""
    
    # Model Configuration
    model_name: WhisperModel = Field(default=WhisperModel.BASE, description="Model size/accuracy tradeoff")
    language: Optional[str] = Field(default=None, description="Language code or None for auto-detect")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Randomness in transcription")
    
    # Audio Processing
    input_sample_rate: int = Field(default=16000, description="Whisper's optimal input rate")
    chunk_length_s: float = Field(default=30.0, ge=5.0, le=180.0, description="Audio chunk length")
    
    # Performance Limits
    max_concurrent_transcriptions: int = Field(default=2, ge=1, le=10, description="Max concurrent STT requests")
    transcription_timeout: float = Field(default=60.0, ge=10.0, le=600.0, description="Transcription timeout")
    
    # Quality Thresholds
    no_speech_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Silence detection threshold")
    logprob_threshold: float = Field(default=-1.0, ge=-10.0, le=0.0, description="Log probability threshold")
    compression_ratio_threshold: float = Field(default=2.4, ge=1.0, le=10.0, description="Repetition detection")
    
    # Streaming Configuration
    enable_streaming: bool = Field(default=False, description="Enable streaming transcription")
    stream_chunk_duration_s: float = Field(default=1.0, ge=0.1, le=5.0, description="Streaming chunk duration")
    
    @validator('language')
    def validate_language_code(cls, v):
        """Validate language code format"""
        if v is not None and len(v) != 2:
            raise ValueError(f"Language code should be 2 characters (e.g., 'en'), got '{v}'")
        return v
    
    @computed_field
    @property
    def model_size_mb(self) -> int:
        """Approximate model size in MB"""
        sizes = {
            WhisperModel.TINY: 39,
            WhisperModel.BASE: 74,
            WhisperModel.SMALL: 244,
            WhisperModel.MEDIUM: 769,
            WhisperModel.LARGE: 1550
        }
        return sizes.get(self.model_name, 74)
    
    class Config:
        use_enum_values = True
        extra = "ignore"
"""
Speech-to-Text Services Package

Provides STT services with integrated Voice Activity Detection:
- WhisperService: OpenAI Whisper-based speech recognition
- StreamingSTTService: Real-time streaming speech-to-text
- VADService: Voice Activity Detection for speech preprocessing
"""

from .whisper_service import WhisperService
from .vad_service import (
    VADService,
    VADConfig,
    VADSensitivity,
    VADState,
    VADResult,
    SpeechSegment
)

# streaming_stt_service contains utility functions, not a class
from . import streaming_stt_service

__all__ = [
    "WhisperService",
    "VADService",
    "VADConfig", 
    "VADSensitivity",
    "VADState",
    "VADResult",
    "SpeechSegment",
    "streaming_stt_service"
]
"""
LLM Function Tools Package

Provides simplified tools for PydanticAI agents with ultra-fast emotion processing:

- simple_llm_service: Clean two-stage emotion processing (emotion query -> response)
- simple_emotion_detector: Single-word emotion detection without JSON complexity
- compact_voice_controller: N-dimensional emotion space with mathematical voice mapping
- sbert_emotion_detector: Lightning-fast SBERT-based emotion detection (5-50ms vs 200-400ms API)
"""

# NEW SIMPLIFIED ARCHITECTURE
from .simple_llm_service import SimpleLLMService, SimpleEmotionalResponse, CharacterProfile
from .simple_emotion_detector import SimpleEmotionDetector, EmotionalResponseGenerator
from .compact_voice_controller import CompactVoiceController, EmotionVector
from .sbert_emotion_detector import SBERTEmotionDetector, EmotionTemplate

__all__ = [
    # CORE SERVICES
    "SimpleLLMService", "SimpleEmotionalResponse", "CharacterProfile",
    "SimpleEmotionDetector", "EmotionalResponseGenerator", 
    "CompactVoiceController", "EmotionVector",
    "SBERTEmotionDetector", "EmotionTemplate"
]
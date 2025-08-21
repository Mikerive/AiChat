"""
LLM Function Tools Package

Provides modular function tools for PydanticAI agents:
- emotion_tools: Emotion detection, analysis, and control
- voice_tools: Voice settings and TTS control
- memory_tools: Conversation memory and context management
- character_tools: Character-specific behaviors and responses
"""

from .emotion_tools import EmotionTool
from .voice_tools import VoiceTool
from .memory_tools import MemoryTool
from .character_tools import CharacterTool

__all__ = ["EmotionTool", "VoiceTool", "MemoryTool", "CharacterTool"]
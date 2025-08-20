"""
Discord integration module for VtuberMiku

This module provides comprehensive Discord bot functionality including:
- Bot connection and authentication
- Voice channel management
- Real-time audio capture from Discord calls
- Voice activity detection
- User tracking and presence monitoring
- Audio transcription integration
"""

from .discord_bot import DiscordBot
from .voice_receiver import VoiceReceiver, AudioFrame
from .voice_gateway import VoiceGateway
from .audio_processor import AudioProcessor, AudioBuffer
from .voice_activity_detector import VoiceActivityDetector
from .user_tracker import UserTracker, DiscordUser
from .config import DiscordConfig

__all__ = [
    'DiscordBot',
    'VoiceReceiver',
    'AudioFrame',
    'VoiceGateway', 
    'AudioProcessor',
    'AudioBuffer',
    'VoiceActivityDetector',
    'UserTracker',
    'DiscordUser',
    'DiscordConfig'
]
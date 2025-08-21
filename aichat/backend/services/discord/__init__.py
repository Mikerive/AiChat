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

from .audio_processor import AudioBuffer, AudioProcessor
from .config import DiscordConfig
from .discord_bot import DiscordBot
from .user_tracker import DiscordUser, UserTracker
from .voice_activity_detector import VoiceActivityDetector
from .voice_gateway import VoiceGateway
from .voice_receiver import AudioFrame, VoiceReceiver

__all__ = [
    "DiscordBot",
    "VoiceReceiver",
    "AudioFrame",
    "VoiceGateway",
    "AudioProcessor",
    "AudioBuffer",
    "VoiceActivityDetector",
    "UserTracker",
    "DiscordUser",
    "DiscordConfig",
]

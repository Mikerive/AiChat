"""
AI Chat - AI-powered chat application with voice cloning

A comprehensive platform for AI chat interactions with voice cloning, real-time chat,
and intelligent character conversations.
"""

__version__ = "1.0.0"
__author__ = "AI Chat Team"

# Core exports
from .core.config import get_settings
from .core.database import get_db
from .core.event_system import get_event_system

__all__ = [
    "get_settings",
    "get_db",
    "get_event_system",
]

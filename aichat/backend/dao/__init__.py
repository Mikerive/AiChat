"""
Data Access Object Layer

Handles all data persistence operations:
- SettingsDAO: JSON configuration files
- CharacterDAO: Character database operations
- ChatLogDAO: Conversation history database operations
"""

from .base_dao import BaseDAO
from .character_dao import CharacterDAO
from .chat_log_dao import ChatLogDAO
from .settings_dao import SettingsDAO, SettingsError

__all__ = ["BaseDAO", "SettingsDAO", "SettingsError", "CharacterDAO", "ChatLogDAO"]

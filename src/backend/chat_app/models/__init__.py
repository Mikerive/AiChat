"""
Models Package

Data models with Pydantic validation for the chat application.
Pure data containers with computed fields and validation.
"""

from .vad_constants import VADConstants, VADSensitivityPreset
from .audio_constants import AudioConstants, AudioQuality, AudioFormat  
from .discord_constants import DiscordConstants, VADSensitivity
from .tts_constants import TTSConstants
from .stt_constants import STTConstants, WhisperModel

# Import DAO for settings persistence
from ..dao import SettingsDAO, SettingsError

# Global settings DAO instance
settings_dao = SettingsDAO()

# Load default model instances
vad_model = VADConstants()
audio_model = AudioConstants()
discord_model = DiscordConstants()
tts_model = TTSConstants()
stt_model = STTConstants()

__all__ = [
    # Data Models
    'VADConstants',
    'AudioConstants', 
    'DiscordConstants',
    'TTSConstants',
    'STTConstants',
    
    # Enums
    'VADSensitivityPreset',
    'AudioQuality',
    'AudioFormat',
    'VADSensitivity',
    'WhisperModel',
    
    # DAO
    'SettingsDAO',
    'SettingsError',
    'settings_dao',
    
    # Model Instances
    'vad_model',
    'audio_model',
    'discord_model',
    'tts_model',
    'stt_model'
]
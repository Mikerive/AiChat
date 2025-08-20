"""
Discord Voice Activity Detection Adapter

Provides a Discord-specific adapter for the core VAD service.
This bridges Discord audio streams with the universal VAD service.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

try:
    from audio_services.vad_service import VADService, VADConfig, VADResult, SpeechSegment, VADState
except ImportError:
    # Fallback imports if audio_services not in path
    from ...audio_services.vad_service import VADService, VADConfig, VADResult, SpeechSegment, VADState

# Import models and DAO
try:
    from ...models import vad_model, settings_dao
    from ...models.vad_constants import VADSensitivityPreset
except ImportError:
    # Fallback if constants not available
    class MockVADConstants:
        def get_effective_energy_threshold(self): return -40.0
        def get_webrtc_aggressiveness(self): return 2
        webrtc_frame_duration_ms = 20
        min_speech_duration_ms = 300
        max_silence_duration_ms = 1000
        noise_suppression_enabled = True
    
    vad_model = MockVADConstants()
    settings_dao = None
    
    class VADSensitivityPreset:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"

from .config import VADSensitivity

logger = logging.getLogger(__name__)


class DiscordVADAdapter:
    """Discord-specific adapter for the universal VAD service"""
    
    def __init__(self, discord_config):
        self.discord_config = discord_config
        
        # Create VAD configuration using centralized constants with Discord overrides
        vad_config_overrides = {
            'sample_rate': discord_config.sample_rate,
            'min_speech_duration': discord_config.vad_min_duration,
            'max_silence_duration': discord_config.vad_silence_timeout,
            'enable_preprocessing': discord_config.enable_noise_suppression,
            'save_speech_segments': True,
            'sensitivity': self._convert_sensitivity(discord_config.vad_sensitivity)
        }
        
        # Use centralized constants with Discord-specific overrides
        try:
            vad_config = VADConfig.from_constants(vad_config_overrides)
        except (AttributeError, TypeError):
            # Fallback to direct construction if from_constants not available
            vad_config = VADConfig(**vad_config_overrides)
        
        # Initialize VAD service
        self.vad_service = VADService(vad_config)
        
        # Discord-specific state tracking
        self.user_mappings: Dict[int, str] = {}  # Maps Discord user_id to VAD source_id
        
        # Callbacks
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None
        self.on_speech_detected: Optional[Callable] = None
        
        # Set up VAD service callbacks
        self.vad_service.set_callbacks(
            speech_end=self._on_vad_speech_end,
            vad_result=self._on_vad_result
        )
        
        logger.info("Discord VAD Adapter initialized")
    
    def _convert_sensitivity(self, discord_sensitivity: VADSensitivity):
        """Convert Discord VAD sensitivity to core VAD sensitivity using centralized constants"""
        try:
            from audio_services.vad_service import VADSensitivity as CoreVADSensitivity
            
            mapping = {
                VADSensitivity.LOW: CoreVADSensitivity.LOW,
                VADSensitivity.MEDIUM: CoreVADSensitivity.MEDIUM,
                VADSensitivity.HIGH: CoreVADSensitivity.HIGH
            }
            return mapping.get(discord_sensitivity, CoreVADSensitivity.MEDIUM)
        except ImportError:
            # If legacy conversion fails, return the discord sensitivity directly
            return discord_sensitivity
    
    async def start(self):
        """Start the VAD adapter"""
        await self.vad_service.start()
        logger.info("Discord VAD Adapter started")
    
    async def stop(self):
        """Stop the VAD adapter"""
        await self.vad_service.stop()
        logger.info("Discord VAD Adapter stopped")
    
    async def process_audio_frame(self, user_id: int, audio_data: bytes, timestamp: float) -> Optional[VADResult]:
        """Process an audio frame for a Discord user"""
        try:
            # Convert Discord user_id to VAD source_id
            source_id = f"discord_user_{user_id}"
            self.user_mappings[user_id] = source_id
            
            # Process through VAD service
            result = await self.vad_service.process_audio_frame(source_id, audio_data, timestamp)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing audio frame for Discord user {user_id}: {e}")
            return None
    
    async def _on_vad_speech_end(self, segment: SpeechSegment, audio_file: Optional[Path]):
        """Handle speech end from VAD service"""
        try:
            # Extract Discord user_id from source_id
            if segment.source_id.startswith("discord_user_"):
                user_id_str = segment.source_id.replace("discord_user_", "")
                try:
                    user_id = int(user_id_str)
                    
                    # Call Discord-specific callback
                    if self.on_speech_end:
                        await self.on_speech_end(user_id, segment, audio_file)
                        
                except ValueError:
                    logger.error(f"Invalid user_id in source_id: {segment.source_id}")
        
        except Exception as e:
            logger.error(f"Error handling VAD speech end: {e}")
    
    async def _on_vad_result(self, result: VADResult):
        """Handle VAD result from VAD service"""
        try:
            # Extract Discord user_id from source_id
            if result.source_id.startswith("discord_user_"):
                user_id_str = result.source_id.replace("discord_user_", "")
                try:
                    user_id = int(user_id_str)
                    
                    # Call Discord-specific callback
                    if self.on_speech_detected:
                        await self.on_speech_detected(user_id, result)
                        
                except ValueError:
                    logger.error(f"Invalid user_id in source_id: {result.source_id}")
        
        except Exception as e:
            logger.error(f"Error handling VAD result: {e}")
    
    def get_user_state(self, user_id: int) -> Optional[VADState]:
        """Get current VAD state for a Discord user"""
        source_id = f"discord_user_{user_id}"
        return self.vad_service.get_source_state(source_id)
    
    def get_active_speakers(self) -> List[int]:
        """Get list of Discord users currently speaking"""
        active_sources = self.vad_service.get_active_sources()
        active_users = []
        
        for source_id in active_sources:
            if source_id.startswith("discord_user_"):
                try:
                    user_id = int(source_id.replace("discord_user_", ""))
                    active_users.append(user_id)
                except ValueError:
                    continue
        
        return active_users
    
    def remove_user(self, user_id: int):
        """Remove Discord user from VAD tracking"""
        source_id = f"discord_user_{user_id}"
        
        # Remove from VAD service
        self.vad_service.remove_source(source_id)
        
        # Remove from mappings
        self.user_mappings.pop(user_id, None)
        
        logger.debug(f"Removed VAD tracking for Discord user {user_id}")
    
    def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Get VAD statistics for a Discord user"""
        source_id = f"discord_user_{user_id}"
        return self.vad_service.get_source_stats(source_id)
    
    def get_stats(self) -> Dict:
        """Get comprehensive VAD statistics"""
        vad_stats = self.vad_service.get_all_stats()
        
        # Add Discord-specific information
        discord_users = len([s for s in vad_stats.get("sources", {}).keys() 
                           if s.startswith("discord_user_")])
        
        # Include centralized constants info
        constants_info = {
            "effective_energy_threshold": vad_model.effective_energy_threshold_db,
            "webrtc_aggressiveness": vad_model.effective_webrtc_aggressiveness,
            "sensitivity_preset": getattr(vad_model, 'sensitivity_preset', 'unknown'),
            "constants_source": "centralized" if settings_dao else "fallback"
        }
        
        return {
            **vad_stats,
            "discord_users_tracked": discord_users,
            "discord_config": {
                "sensitivity": self.discord_config.vad_sensitivity.value,
                "min_duration": self.discord_config.vad_min_duration,
                "silence_timeout": self.discord_config.vad_silence_timeout
            },
            "vad_constants": constants_info
        }
    
    def set_callbacks(self, **callbacks):
        """Set Discord-specific callback functions"""
        for name, callback in callbacks.items():
            if hasattr(self, f"on_{name}"):
                setattr(self, f"on_{name}", callback)
    
    async def cleanup(self):
        """Cleanup adapter resources"""
        await self.vad_service.cleanup()
        self.user_mappings.clear()
        logger.info("Discord VAD Adapter cleaned up")


# For backward compatibility, create an alias
VoiceActivityDetector = DiscordVADAdapter
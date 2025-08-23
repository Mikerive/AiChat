"""
Discord service for receiving voice inputs from Discord calls and tracking users

This is the main Discord service that orchestrates all Discord functionality including
voice capture, user tracking, and integration with VtuberMiku's voice processing pipeline.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Third-party imports
try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    discord = None
    commands = None

# Local imports
from aichat.constants.paths import TEMP_AUDIO_DIR, ensure_dirs
from aichat.core.event_system import EventSeverity, EventType, get_event_system
from .config import DiscordConfig
from .discord_bot import DiscordBot

logger = logging.getLogger(__name__)

@dataclass
class DiscordServiceConfig:
    """Discord service configuration - simplified interface"""

    bot_token: Optional[str] = None
    guild_id: Optional[int] = None
    voice_channel_id: Optional[int] = None
    text_channel_id: Optional[int] = None
    auto_join_voice: bool = True
    record_audio: bool = True
    track_speaking: bool = True
    enable_transcription: bool = True

class DiscordService:
    """Main Discord service for VtuberMiku voice integration"""

    def __init__(self, config: Optional[DiscordServiceConfig] = None):
        self.config = config or DiscordServiceConfig()
        self.event_system = get_event_system()

        # Convert to full Discord config
        self.discord_config = self._convert_config(self.config)

        # Discord bot instance
        self.discord_bot: Optional[DiscordBot] = None

        # Connection state
        self.is_running = False
        self.is_connected = False

        # VtuberMiku service integration
        self.whisper_service = None
        self.tts_service = None
        self.chat_service = None

        # Callbacks
        self.on_user_message: Optional[Callable] = None
        self.on_transcription: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # Statistics
        self.stats = {
            "start_time": None,
            "connections": 0,
            "messages_processed": 0,
            "transcriptions": 0,
            "errors": 0,
        }

        # Initialize directories
        ensure_dirs(TEMP_AUDIO_DIR)

        logger.info("Discord Service initialized")

    def _convert_config(self, simple_config: DiscordServiceConfig) -> DiscordConfig:
        """Convert simple config to full Discord config"""
        return DiscordConfig(
            bot_token=simple_config.bot_token,
            guild_id=simple_config.guild_id,
            voice_channel_id=simple_config.voice_channel_id,
            text_channel_id=simple_config.text_channel_id,
            auto_join_voice=simple_config.auto_join_voice,
            record_audio=simple_config.record_audio,
            track_speaking=simple_config.track_speaking,
            enable_transcription=simple_config.enable_transcription,
            # Use sensible defaults for advanced settings
            enable_vad=True,
            vad_min_duration=0.3,
            vad_silence_timeout=1.0,
            enable_noise_suppression=True,
            require_user_consent=True,
            sample_rate=16000,
            channels=1,
        )

    async def start(self, bot_token: Optional[str] = None) -> bool:
        """Start the Discord service"""
        if not DISCORD_AVAILABLE:
            logger.error(
                "Discord.py not available. Install with: pip install discord.py[voice]"
            )
            await self._emit_error("Discord.py not available")
            return False

        try:
            if self.is_running:
                logger.warning("Discord service already running")
                return True

            # Use provided token or config token
            token = bot_token or self.config.bot_token
            if not token:
                logger.error("No Discord bot token provided")
                await self._emit_error("No Discord bot token provided")
                return False

            # Create Discord bot
            self.discord_bot = DiscordBot(self.discord_config)

            # Set up service integrations
            await self.discord_bot.set_services(
                whisper_service=self.whisper_service,
                tts_service=self.tts_service,
                chat_service=self.chat_service,
            )

            # Set up callbacks
            self.discord_bot.set_callbacks(
                ready=self._on_bot_ready,
                user_message=self._on_user_message,
                transcription=self._on_transcription,
                error=self._on_error,
            )

            # Start the bot
            self.is_running = True
            self.stats["start_time"] = time.time()

            # Start bot in background task
            asyncio.create_task(self.discord_bot.start(token))

            logger.info("Discord service started")
            return True

        except Exception as e:
            logger.error(f"Error starting Discord service: {e}")
            self.is_running = False
            await self._emit_error(f"Failed to start Discord service: {e}")
            return False

    async def stop(self):
        """Stop the Discord service"""
        try:
            self.is_running = False
            self.is_connected = False

            if self.discord_bot:
                await self.discord_bot.stop()
                self.discord_bot = None

            await self.event_system.emit(
                EventType.WEBSOCKET_DISCONNECTED,
                "Discord service stopped",
                {"service": "discord"},
            )

            logger.info("Discord service stopped")

        except Exception as e:
            logger.error(f"Error stopping Discord service: {e}")

    async def join_voice_channel(self, channel_id: int) -> bool:
        """Join a specific voice channel"""
        if not self.discord_bot:
            logger.error("Discord bot not started")
            return False

        return await self.discord_bot.join_voice_channel(channel_id)

    async def leave_voice_channel(self):
        """Leave current voice channel"""
        if self.discord_bot:
            await self.discord_bot.leave_voice_channel()

    async def send_message(self, channel_id: int, message: str) -> bool:
        """Send a text message to a Discord channel"""
        if not self.discord_bot:
            logger.error("Discord bot not started")
            return False

        return await self.discord_bot.send_message(channel_id, message)

    async def play_audio(self, audio_file: Path) -> bool:
        """Play audio in current voice channel"""
        if not self.discord_bot:
            logger.error("Discord bot not started")
            return False

        return await self.discord_bot.play_audio(audio_file)

    async def set_services(
        self, whisper_service=None, tts_service=None, chat_service=None
    ):
        """Set VtuberMiku services for integration"""
        self.whisper_service = whisper_service
        self.tts_service = tts_service
        self.chat_service = chat_service

        # Update bot services if running
        if self.discord_bot:
            await self.discord_bot.set_services(
                whisper_service=whisper_service,
                tts_service=tts_service,
                chat_service=chat_service,
            )

        logger.info("Discord service VtuberMiku integrations configured")

    # Event handlers
    async def _on_bot_ready(self):
        """Handle bot ready event"""
        self.is_connected = True
        self.stats["connections"] += 1

        await self.event_system.emit(
            EventType.WEBSOCKET_CONNECTED,
            "Discord bot connected and ready",
            {"service": "discord", "connections": self.stats["connections"]},
        )

        logger.info("Discord bot connected and ready")

    async def _on_user_message(self, message_data: Dict[str, Any]):
        """Handle processed user message from Discord"""
        try:
            self.stats["messages_processed"] += 1

            await self.event_system.emit(
                EventType.AUDIO_TRANSCRIBED,
                f"Message from Discord user: {message_data.get('user_name', 'Unknown')}",
                message_data,
            )

            # Call external callback
            if self.on_user_message:
                await self.on_user_message(message_data)

            logger.debug(
                f"Processed Discord message: {message_data.get('message', '')}"
            )

        except Exception as e:
            logger.error(f"Error handling user message: {e}")

    async def _on_transcription(self, transcription_result):
        """Handle transcription result"""
        try:
            self.stats["transcriptions"] += 1

            # Call external callback
            if self.on_transcription:
                await self.on_transcription(transcription_result)

        except Exception as e:
            logger.error(f"Error handling transcription: {e}")

    async def _on_error(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Handle error from Discord bot"""
        try:
            self.stats["errors"] += 1

            await self._emit_error(message, data)

            # Call external callback
            if self.on_error:
                await self.on_error(message, data)

        except Exception as e:
            logger.error(f"Error handling Discord error: {e}")

    def get_connected_users(self) -> List[Dict[str, Any]]:
        """Get list of users currently in voice channels"""
        if not self.discord_bot:
            return []

        try:
            users = self.discord_bot.user_tracker.get_all_users()
            return [user.to_dict() for user in users]
        except Exception as e:
            logger.error(f"Error getting connected users: {e}")
            return []

    def get_speaking_users(self) -> List[Dict[str, Any]]:
        """Get list of users currently speaking"""
        if not self.discord_bot:
            return []

        try:
            users = self.discord_bot.user_tracker.get_speaking_users()
            return [user.to_dict() for user in users]
        except Exception as e:
            logger.error(f"Error getting speaking users: {e}")
            return []

    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive service status"""
        try:
            # Get bot status if available
            bot_status = {}
            if self.discord_bot:
                bot_status = await self.discord_bot.get_status()

            # Calculate uptime
            uptime = 0.0
            if self.stats["start_time"]:
                uptime = time.time() - self.stats["start_time"]

            return {
                "running": self.is_running,
                "connected": self.is_connected,
                "available": DISCORD_AVAILABLE,
                "uptime": uptime,
                "stats": self.stats,
                "config": {
                    "auto_join_voice": self.config.auto_join_voice,
                    "record_audio": self.config.record_audio,
                    "track_speaking": self.config.track_speaking,
                    "enable_transcription": self.config.enable_transcription,
                },
                "bot": bot_status,
            }

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"running": False, "connected": False, "error": str(e)}

    def set_callbacks(self, **callbacks):
        """Set callback functions"""
        for name, callback in callbacks.items():
            if hasattr(self, f"on_{name}"):
                setattr(self, f"on_{name}", callback)

    async def _emit_error(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Emit error event"""
        await self.event_system.emit(
            EventType.ERROR_OCCURRED, message, data or {}, EventSeverity.ERROR
        )

    def is_voice_connected(self) -> bool:
        """Check if connected to voice channel"""
        if self.discord_bot:
            return self.discord_bot.is_voice_connected()
        return False

    async def cleanup(self):
        """Cleanup service resources"""
        await self.stop()
        logger.info("Discord service cleaned up")

# Alias for backward compatibility
DiscordUser = dict  # Simple dict representation for user data

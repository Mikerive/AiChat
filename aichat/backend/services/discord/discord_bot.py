"""
Main Discord Bot Implementation

Orchestrates all Discord components including voice gateway, audio processing,
user tracking, and integration with VtuberMiku services.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional
from pathlib import Path

try:
    import discord
    from discord.ext import commands

    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    discord = None
    commands = None

try:
    from aichat.core.event_system import EventSeverity, EventType, get_event_system
except ImportError:
    # Fallback for when imports aren't available
    def get_event_system():
        class MockEventSystem:
            async def emit(self, *args, **kwargs):
                pass

        return MockEventSystem()

    class EventType:
        WEBSOCKET_CONNECTED = "websocket_connected"
        WEBSOCKET_DISCONNECTED = "websocket_disconnected"
        ERROR_OCCURRED = "error_occurred"
        AUDIO_TRANSCRIBED = "audio_transcribed"

    class EventSeverity:
        ERROR = "error"


logger = logging.getLogger(__name__)


class DiscordBot:
    """Main Discord bot with full voice capture and processing capabilities"""

    def __init__(self, config: DiscordConfig):
        self.config = config
        self.event_system = get_event_system()

        # Discord bot instance
        self.bot: Optional[commands.Bot] = None
        self.voice_client: Optional[discord.VoiceClient] = None

        # Core components
        self.user_tracker = UserTracker(config)
        self.voice_receiver: Optional[VoiceReceiver] = None
        self.audio_processor: Optional[AudioProcessor] = None

        # Connection state
        self.is_running = False
        self.current_guild_id: Optional[int] = None
        self.current_voice_channel_id: Optional[int] = None

        # VtuberMiku service integration
        self.whisper_service = None
        self.tts_service = None
        self.chat_service = None

        # Callbacks
        self.on_ready: Optional[Callable] = None
        self.on_user_message: Optional[Callable] = None
        self.on_transcription: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # Statistics
        self.stats = {
            "start_time": None,
            "uptime": 0.0,
            "voice_connections": 0,
            "messages_processed": 0,
            "errors": 0,
        }

        logger.info("Discord Bot initialized")

    async def start(self, bot_token: str) -> bool:
        """Start the Discord bot"""
        if not DISCORD_AVAILABLE:
            logger.error(
                "Discord.py not available. Install with: pip install discord.py[voice]"
            )
            return False

        try:
            if self.is_running:
                logger.warning("Bot is already running")
                return True

            # Create Discord bot with required intents
            intents = discord.Intents.default()
            intents.voice_states = True
            intents.guilds = True
            intents.members = True
            intents.message_content = True

            self.bot = commands.Bot(command_prefix="!miku ", intents=intents)

            # Register event handlers
            self._register_event_handlers()

            # Set up components
            await self._setup_components()

            # Start bot
            logger.info("Starting Discord bot...")
            await self.bot.start(bot_token)

            return True

        except Exception as e:
            logger.error(f"Failed to start Discord bot: {e}")
            await self._emit_error(f"Bot startup failed: {e}")
            return False

    async def stop(self):
        """Stop the Discord bot"""
        try:
            self.is_running = False

            # Stop audio processing
            if self.audio_processor:
                await self.audio_processor.stop()

            # Stop voice receiver
            if self.voice_receiver:
                await self.voice_receiver.stop_receiving()

            # Leave voice channel
            if self.voice_client:
                await self.voice_client.disconnect()
                self.voice_client = None

            # Close bot connection
            if self.bot:
                await self.bot.close()
                self.bot = None

            # Clean up user tracker
            await self.user_tracker.cleanup()

            await self.event_system.emit(
                EventType.WEBSOCKET_DISCONNECTED,
                "Discord bot stopped",
                {"service": "discord"},
            )

            logger.info("Discord bot stopped")

        except Exception as e:
            logger.error(f"Error stopping Discord bot: {e}")

    async def _setup_components(self):
        """Set up bot components"""
        try:
            # Initialize voice receiver
            self.voice_receiver = VoiceReceiver(self.config, self.user_tracker)

            # Initialize audio processor
            self.audio_processor = AudioProcessor(self.config, self.user_tracker)

            # Set up callbacks between components
            self.voice_receiver.set_callbacks(
                speech_completed=self._on_speech_completed,
                audio_received=self._on_audio_received,
            )

            self.audio_processor.set_callbacks(
                transcription_complete=self._on_transcription_complete,
                user_message=self._on_user_message,
                processing_error=self._on_processing_error,
            )

            self.user_tracker.set_callbacks(
                user_join=self._on_user_join,
                user_leave=self._on_user_leave,
                user_start_speaking=self._on_user_start_speaking,
                user_stop_speaking=self._on_user_stop_speaking,
                user_consent_granted=self._on_user_consent_granted,
            )

            # Set services for audio processor
            await self.audio_processor.set_services(
                whisper_service=self.whisper_service,
                tts_service=self.tts_service,
                chat_service=self.chat_service,
            )

            # Start audio processor
            await self.audio_processor.start()

            logger.info("Discord bot components set up successfully")

        except Exception as e:
            logger.error(f"Error setting up components: {e}")
            raise

    def _register_event_handlers(self):
        """Register Discord bot event handlers"""
        if not self.bot:
            return

        @self.bot.event
        async def on_ready():
            """Bot is ready and connected"""
            try:
                self.is_running = True
                self.stats["start_time"] = time.time()

                await self.event_system.emit(
                    EventType.WEBSOCKET_CONNECTED,
                    f"Discord bot connected as {self.bot.user}",
                    {
                        "bot_name": str(self.bot.user),
                        "bot_id": self.bot.user.id,
                        "guild_count": len(self.bot.guilds),
                        "service": "discord",
                    },
                )

                # Auto-join voice channel if configured
                if self.config.auto_join_voice:
                    await self._auto_join_voice_channel()

                # Call custom ready callback
                if self.on_ready:
                    await self.on_ready()

                logger.info(f"Discord bot ready: {self.bot.user}")

            except Exception as e:
                logger.error(f"Error in on_ready: {e}")
                await self._emit_error(f"Ready event error: {e}")

        @self.bot.event
        async def on_voice_state_update(member, before, after):
            """Handle voice state changes"""
            try:
                await self.user_tracker.handle_voice_state_update(member, before, after)
            except Exception as e:
                logger.error(f"Error handling voice state update: {e}")

        @self.bot.event
        async def on_message(message):
            """Handle text messages"""
            try:
                if message.author.bot:
                    return

                # Process commands
                await self.bot.process_commands(message)

                # Handle regular messages if needed
                await self._handle_text_message(message)

            except Exception as e:
                logger.error(f"Error handling message: {e}")

        @self.bot.event
        async def on_disconnect():
            """Handle bot disconnect"""
            try:
                await self.event_system.emit(
                    EventType.WEBSOCKET_DISCONNECTED,
                    "Discord bot disconnected",
                    {"service": "discord"},
                )
                logger.warning("Discord bot disconnected")
            except Exception as e:
                logger.error(f"Error handling disconnect: {e}")

        @self.bot.event
        async def on_error(event, *args, **kwargs):
            """Handle bot errors"""
            try:
                logger.error(f"Discord bot error in {event}: {args}")
                self.stats["errors"] += 1
                await self._emit_error(f"Bot error in {event}")
            except Exception:
                pass

        # Register commands
        self._register_commands()

    def _register_commands(self):
        """Register Discord bot commands"""
        if not self.bot:
            return

        @self.bot.command(name="join")
        async def join_voice(ctx, channel_id: int = None):
            """Join a voice channel"""
            try:
                if channel_id:
                    success = await self.join_voice_channel(channel_id)
                else:
                    # Join the user's current voice channel
                    if ctx.author.voice and ctx.author.voice.channel:
                        success = await self.join_voice_channel(
                            ctx.author.voice.channel.id
                        )
                    else:
                        await ctx.send(
                            "You need to be in a voice channel or specify a channel ID!"
                        )
                        return

                if success:
                    await ctx.send(f"Joined voice channel!")
                else:
                    await ctx.send("Failed to join voice channel.")

            except Exception as e:
                logger.error(f"Error in join command: {e}")
                await ctx.send("Error joining voice channel.")

        @self.bot.command(name="leave")
        async def leave_voice(ctx):
            """Leave voice channel"""
            try:
                await self.leave_voice_channel()
                await ctx.send("Left voice channel!")
            except Exception as e:
                logger.error(f"Error in leave command: {e}")
                await ctx.send("Error leaving voice channel.")

        @self.bot.command(name="status")
        async def bot_status(ctx):
            """Get bot status"""
            try:
                status = await self.get_status()

                embed = discord.Embed(
                    title="VtuberMiku Discord Bot Status", color=0x00FF00
                )
                embed.add_field(
                    name="Connected", value=status["connected"], inline=True
                )
                embed.add_field(
                    name="Voice Channel",
                    value=status.get("voice_channel", "None"),
                    inline=True,
                )
                embed.add_field(
                    name="Users Tracked", value=status["users"]["total"], inline=True
                )
                embed.add_field(
                    name="Speaking Users",
                    value=status["users"]["speaking"],
                    inline=True,
                )
                embed.add_field(
                    name="Uptime", value=f"{status['uptime']:.1f}s", inline=True
                )

                await ctx.send(embed=embed)

            except Exception as e:
                logger.error(f"Error in status command: {e}")
                await ctx.send("Error getting status.")

        @self.bot.command(name="consent")
        async def grant_consent(ctx):
            """Grant recording consent"""
            try:
                success = self.user_tracker.grant_user_consent(ctx.author.id)
                if success:
                    await ctx.send(
                        "Recording consent granted! Your voice will now be processed."
                    )
                else:
                    await ctx.send("You need to be in a voice channel first.")
            except Exception as e:
                logger.error(f"Error in consent command: {e}")
                await ctx.send("Error granting consent.")

        @self.bot.command(name="revoke")
        async def revoke_consent(ctx):
            """Revoke recording consent"""
            try:
                success = self.user_tracker.revoke_user_consent(ctx.author.id)
                if success:
                    await ctx.send(
                        "Recording consent revoked. Your voice will no longer be processed."
                    )
                else:
                    await ctx.send("You don't have active consent to revoke.")
            except Exception as e:
                logger.error(f"Error in revoke command: {e}")
                await ctx.send("Error revoking consent.")

    async def _auto_join_voice_channel(self):
        """Automatically join configured voice channel"""
        try:
            if self.config.voice_channel_id:
                await self.join_voice_channel(self.config.voice_channel_id)
            else:
                # Find first available voice channel with members
                for guild in self.bot.guilds:
                    for channel in guild.voice_channels:
                        if len(channel.members) > 0:
                            await self.join_voice_channel(channel.id)
                            return
                logger.info("No voice channels with members found for auto-join")

        except Exception as e:
            logger.error(f"Error auto-joining voice channel: {e}")

    async def join_voice_channel(self, channel_id: int) -> bool:
        """Join a specific voice channel"""
        try:
            if not self.bot:
                logger.error("Bot not connected")
                return False

            channel = self.bot.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.VoiceChannel):
                logger.error(f"Voice channel not found: {channel_id}")
                return False

            # Leave current channel if connected
            if self.voice_client:
                await self.voice_client.disconnect()
                await self.voice_receiver.stop_receiving()

            # Join new channel
            self.voice_client = await channel.connect()
            self.current_voice_channel_id = channel_id
            self.current_guild_id = channel.guild.id
            self.stats["voice_connections"] += 1

            # Start receiving audio if configured
            if self.config.record_audio and self.voice_receiver:
                success = await self.voice_receiver.start_receiving(self.voice_client)
                if not success:
                    logger.error("Failed to start voice receiver")
                    return False

            await self.event_system.emit(
                EventType.WEBSOCKET_CONNECTED,
                f"Joined voice channel: {channel.name}",
                {
                    "channel_id": channel_id,
                    "channel_name": channel.name,
                    "guild_name": channel.guild.name,
                    "member_count": len(channel.members),
                    "service": "discord",
                },
            )

            logger.info(f"Joined voice channel: {channel.name}")
            return True

        except Exception as e:
            logger.error(f"Error joining voice channel: {e}")
            await self._emit_error(f"Failed to join voice channel: {e}")
            return False

    async def leave_voice_channel(self):
        """Leave current voice channel"""
        try:
            if self.voice_receiver:
                await self.voice_receiver.stop_receiving()

            if self.voice_client:
                await self.voice_client.disconnect()
                self.voice_client = None

            self.current_voice_channel_id = None

            await self.event_system.emit(
                EventType.WEBSOCKET_DISCONNECTED,
                "Left voice channel",
                {"service": "discord"},
            )

            logger.info("Left voice channel")

        except Exception as e:
            logger.error(f"Error leaving voice channel: {e}")

    async def send_message(self, channel_id: int, message: str) -> bool:
        """Send a text message to a Discord channel"""
        try:
            if not self.bot:
                logger.error("Bot not connected")
                return False

            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel not found: {channel_id}")
                return False

            await channel.send(message)
            logger.info(f"Message sent to {channel.name}: {message}")
            return True

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    async def play_audio(self, audio_file: Path) -> bool:
        """Play audio in current voice channel"""
        try:
            if not self.voice_client:
                logger.error("Not connected to voice channel")
                return False

            if not audio_file.exists():
                logger.error(f"Audio file not found: {audio_file}")
                return False

            # Stop current audio if playing
            if self.voice_client.is_playing():
                self.voice_client.stop()

            # Play audio file
            audio_source = discord.FFmpegPCMAudio(str(audio_file))
            self.voice_client.play(audio_source)

            logger.info(f"Playing audio: {audio_file}")
            return True

        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            return False

    # Component event handlers
    async def _on_user_join(self, user: DiscordUser):
        """Handle user joining voice channel"""
        logger.info(f"User joined voice: {user.display_name}")

    async def _on_user_leave(self, user: DiscordUser):
        """Handle user leaving voice channel"""
        logger.info(f"User left voice: {user.display_name}")

        # Clean up audio processing for this user
        if self.voice_receiver:
            self.voice_receiver.remove_user(user.id)

    async def _on_user_start_speaking(self, user: DiscordUser):
        """Handle user starting to speak"""
        logger.debug(f"User started speaking: {user.display_name}")

    async def _on_user_stop_speaking(self, user: DiscordUser):
        """Handle user stopping to speak"""
        logger.debug(f"User stopped speaking: {user.display_name}")

    async def _on_user_consent_granted(self, user: DiscordUser):
        """Handle user granting recording consent"""
        logger.info(f"Recording consent granted by {user.display_name}")

    async def _on_audio_received(self, frame: AudioFrame):
        """Handle received audio frame"""
        # Process through audio processor if needed
        if self.audio_processor:
            await self.audio_processor.process_audio_frame(frame)

    async def _on_speech_completed(
        self, user_id: int, segment: SpeechSegment, audio_file: Path
    ):
        """Handle completed speech segment"""
        if self.audio_processor and audio_file:
            await self.audio_processor.process_speech_segment(
                user_id, segment, audio_file
            )

    async def _on_transcription_complete(self, transcription: TranscriptionResult):
        """Handle completed transcription"""
        self.stats["messages_processed"] += 1

        if self.on_transcription:
            await self.on_transcription(transcription)

    async def _on_user_message(self, message_data: Dict[str, Any]):
        """Handle processed user message"""
        if self.on_user_message:
            await self.on_user_message(message_data)

    async def _on_processing_error(self, user_id: int, error: Exception):
        """Handle processing error"""
        logger.error(f"Processing error for user {user_id}: {error}")
        await self._emit_error(f"Processing error: {error}")

    async def _handle_text_message(self, message):
        """Handle text messages from Discord"""
        # This could be integrated with the chat system

    async def set_services(
        self, whisper_service=None, tts_service=None, chat_service=None
    ):
        """Set VtuberMiku services for integration"""
        self.whisper_service = whisper_service
        self.tts_service = tts_service
        self.chat_service = chat_service

        # Update audio processor services
        if self.audio_processor:
            await self.audio_processor.set_services(
                whisper_service=whisper_service,
                tts_service=tts_service,
                chat_service=chat_service,
            )

        logger.info("VtuberMiku services configured")

    def set_callbacks(self, **callbacks):
        """Set callback functions"""
        for name, callback in callbacks.items():
            if hasattr(self, f"on_{name}"):
                setattr(self, f"on_{name}", callback)

    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive bot status"""
        try:
            # Update uptime
            if self.stats["start_time"]:
                self.stats["uptime"] = time.time() - self.stats["start_time"]

            # Get component stats
            user_stats = self.user_tracker.get_stats()

            voice_receiver_stats = {}
            if self.voice_receiver:
                voice_receiver_stats = self.voice_receiver.get_stats()

            audio_processor_stats = {}
            if self.audio_processor:
                audio_processor_stats = self.audio_processor.get_stats()

            return {
                "connected": self.is_running,
                "bot_user": str(self.bot.user) if self.bot and self.bot.user else None,
                "voice_connected": self.voice_client is not None,
                "voice_channel": {
                    "id": self.current_voice_channel_id,
                    "name": (
                        self.voice_client.channel.name if self.voice_client else None
                    ),
                },
                "guild_id": self.current_guild_id,
                "users": user_stats,
                "voice_receiver": voice_receiver_stats,
                "audio_processor": audio_processor_stats,
                "config": {
                    "auto_join_voice": self.config.auto_join_voice,
                    "record_audio": self.config.record_audio,
                    "enable_vad": self.config.enable_vad,
                    "enable_transcription": self.config.enable_transcription,
                },
                **self.stats,
            }

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"connected": False, "error": str(e)}

    async def _emit_error(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Emit error event"""
        self.stats["errors"] += 1

        await self.event_system.emit(
            EventType.ERROR_OCCURRED, message, data or {}, EventSeverity.ERROR
        )

        if self.on_error:
            await self.on_error(message, data)

    def is_connected(self) -> bool:
        """Check if bot is connected"""
        return self.is_running and self.bot is not None and not self.bot.is_closed()

    def is_voice_connected(self) -> bool:
        """Check if connected to voice channel"""
        return self.voice_client is not None

    async def cleanup(self):
        """Cleanup all resources"""
        await self.stop()
        logger.info("Discord bot cleaned up")

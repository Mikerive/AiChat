"""
Discord Voice Receiver and Audio Processing

Handles receiving, decoding, and processing audio from Discord voice channels.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

try:
    import discord
    import numpy as np
    import soundfile as sf
    from discord.ext import commands

    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    discord = None
    commands = None
    np = None
    sf = None

try:
    from aichat.constants.paths import TEMP_AUDIO_DIR, ensure_dirs
    from aichat.core.event_system import EventSeverity, EventType, get_event_system
except ImportError:
    # Fallback for when imports aren't available
    TEMP_AUDIO_DIR = Path("temp_audio")

    def ensure_dirs(*paths):
        for path in paths:
            Path(path).mkdir(parents=True, exist_ok=True)

    def get_event_system():
        class MockEventSystem:
            async def emit(self, *args, **kwargs):
                pass

        return MockEventSystem()

    class EventType:
        AUDIO_CAPTURED = "audio_captured"
        AUDIO_PROCESSED = "audio_processed"
        ERROR_OCCURRED = "error_occurred"

    class EventSeverity:
        ERROR = "error"


logger = logging.getLogger(__name__)


@dataclass
class AudioFrame:
    """Represents a processed audio frame"""

    user_id: int
    timestamp: float
    audio_data: bytes
    sample_rate: int
    channels: int
    duration: float
    audio_level: float
    is_speech: bool = False
    confidence: float = 0.0


@dataclass
class AudioBuffer:
    """Circular buffer for audio data"""

    user_id: int
    max_duration: float = 10.0  # Maximum buffer duration in seconds
    sample_rate: int = 16000

    def __post_init__(self):
        self.frames: deque = deque()
        self.total_duration = 0.0
        self.last_activity = time.time()

    def add_frame(self, frame: AudioFrame):
        """Add audio frame to buffer"""
        self.frames.append(frame)
        self.total_duration += frame.duration
        self.last_activity = time.time()

        # Remove old frames if buffer is too large
        while self.total_duration > self.max_duration and self.frames:
            old_frame = self.frames.popleft()
            self.total_duration -= old_frame.duration

    def get_recent_audio(self, duration: float) -> List[AudioFrame]:
        """Get recent audio frames within specified duration"""
        recent_frames = []
        accumulated_duration = 0.0

        for frame in reversed(self.frames):
            if accumulated_duration >= duration:
                break
            recent_frames.insert(0, frame)
            accumulated_duration += frame.duration

        return recent_frames

    def clear(self):
        """Clear the buffer"""
        self.frames.clear()
        self.total_duration = 0.0

    def is_empty(self) -> bool:
        """Check if buffer is empty"""
        return len(self.frames) == 0

    def get_duration(self) -> float:
        """Get total duration of buffered audio"""
        return self.total_duration


class VoiceReceiver:
    """Receives and processes audio from Discord voice channels"""

    def __init__(self, config: DiscordConfig, user_tracker: UserTracker):
        self.config = config
        self.user_tracker = user_tracker
        self.event_system = get_event_system()

        # Voice gateway connection
        self.voice_gateway: Optional[VoiceGateway] = None

        # Audio processing
        self.vad = DiscordVADAdapter(config) if config.enable_vad else None
        self.audio_buffers: Dict[int, AudioBuffer] = {}

        # Opus decoder (Discord uses Opus audio codec)
        self.opus_decoders: Dict[int, Any] = {}

        # Audio processing settings
        self.target_sample_rate = config.sample_rate
        self.target_channels = config.channels
        self.frame_duration = 20  # Discord uses 20ms frames
        self.frame_size = int(self.target_sample_rate * self.frame_duration / 1000)

        # Callbacks
        self.on_audio_received: Optional[Callable] = None
        self.on_speech_detected: Optional[Callable] = None
        self.on_speech_completed: Optional[Callable] = None

        # Statistics
        self.stats = {
            "total_packets_received": 0,
            "total_frames_processed": 0,
            "active_buffers": 0,
            "speech_segments_detected": 0,
        }

        # Ensure directories exist
        ensure_dirs(TEMP_AUDIO_DIR)

        logger.info("Voice Receiver initialized")

    async def start_receiving(self, voice_client: discord.VoiceClient) -> bool:
        """Start receiving audio from Discord voice channel"""
        try:
            if not DISCORD_AVAILABLE:
                logger.error("Discord.py not available")
                return False

            # Get voice connection details
            if not hasattr(voice_client, "ws") or not voice_client.ws:
                logger.error("Voice client not properly connected")
                return False

            session_id = voice_client.session_id
            token = voice_client.token
            endpoint = voice_client.endpoint
            user_id = voice_client.user.id

            # Create voice gateway connection
            self.voice_gateway = VoiceGateway(session_id, token, endpoint, user_id)

            # Set up audio callback
            self.voice_gateway.set_audio_callback(self._handle_audio_packet)

            # Connect to voice gateway
            success = await self.voice_gateway.connect()
            if not success:
                logger.error("Failed to connect to voice gateway")
                return False

            # Set up VAD callbacks if enabled
            if self.vad:
                await self.vad.start()
                self.vad.set_callbacks(
                    speech_end=self._on_speech_end,
                    speech_detected=self._on_speech_detected,
                )

            logger.info("Voice receiver started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start voice receiver: {e}")
            return False

    async def stop_receiving(self):
        """Stop receiving audio"""
        try:
            if self.voice_gateway:
                await self.voice_gateway.disconnect()
                self.voice_gateway = None

            # Clear audio buffers
            self.audio_buffers.clear()

            # Clear opus decoders
            self.opus_decoders.clear()

            # Clean up VAD
            if self.vad:
                await self.vad.stop()
                await self.vad.cleanup()

            logger.info("Voice receiver stopped")

        except Exception as e:
            logger.error(f"Error stopping voice receiver: {e}")

    async def _handle_audio_packet(self, packet: VoicePacket):
        """Handle received audio packet from Discord"""
        try:
            self.stats["total_packets_received"] += 1

            if not packet.user_id or not packet.decrypted_data:
                return

            # Check if user is allowed to be recorded
            user = self.user_tracker.get_user(packet.user_id)
            if not user or not user.recording_enabled:
                return

            # Decode Opus audio to PCM
            pcm_data = await self._decode_opus_audio(
                packet.user_id, packet.decrypted_data
            )
            if not pcm_data:
                return

            # Create audio frame
            frame = AudioFrame(
                user_id=packet.user_id,
                timestamp=time.time(),
                audio_data=pcm_data,
                sample_rate=self.target_sample_rate,
                channels=self.target_channels,
                duration=len(pcm_data)
                / (
                    self.target_sample_rate * self.target_channels * 2
                ),  # 16-bit samples
                audio_level=self._calculate_audio_level(pcm_data),
            )

            # Process audio frame
            await self._process_audio_frame(frame)

        except Exception as e:
            logger.error(f"Error handling audio packet: {e}")

    async def _decode_opus_audio(
        self, user_id: int, opus_data: bytes
    ) -> Optional[bytes]:
        """Decode Opus audio data to PCM"""
        try:
            # Get or create Opus decoder for this user
            if user_id not in self.opus_decoders:
                try:
                    import opuslib

                    decoder = opuslib.Decoder(48000, 2)  # Discord uses 48kHz stereo
                    self.opus_decoders[user_id] = decoder
                except ImportError:
                    logger.warning("opuslib not available, using mock audio decoder")
                    self.opus_decoders[user_id] = None

            decoder = self.opus_decoders[user_id]

            if decoder:
                # Decode Opus to PCM
                pcm_data = decoder.decode(opus_data, frame_size=960)  # 20ms at 48kHz

                # Convert to numpy array for processing
                audio_array = np.frombuffer(pcm_data, dtype=np.int16)

                # Reshape if stereo
                if len(audio_array) % 2 == 0:
                    audio_array = audio_array.reshape(-1, 2)
                    # Convert to mono if needed
                    if self.target_channels == 1:
                        audio_array = np.mean(audio_array, axis=1).astype(np.int16)

                # Resample if needed
                if self.target_sample_rate != 48000:
                    audio_array = self._resample_audio(
                        audio_array, 48000, self.target_sample_rate
                    )

                return audio_array.tobytes()
            else:
                # Mock decoder for testing
                # Generate silence with some noise
                samples = int(self.target_sample_rate * 0.02)  # 20ms
                mock_audio = np.random.randint(-1000, 1000, samples, dtype=np.int16)
                return mock_audio.tobytes()

        except Exception as e:
            logger.debug(f"Error decoding opus audio: {e}")
            return None

    def _resample_audio(
        self, audio_array: np.ndarray, original_rate: int, target_rate: int
    ) -> np.ndarray:
        """Resample audio to target sample rate"""
        if original_rate == target_rate:
            return audio_array

        try:
            import librosa

            # Convert to float for resampling
            audio_float = audio_array.astype(np.float32) / 32768.0
            resampled = librosa.resample(
                audio_float, orig_sr=original_rate, target_sr=target_rate
            )
            # Convert back to int16
            return (resampled * 32768.0).astype(np.int16)
        except ImportError:
            # Simple linear interpolation fallback
            ratio = target_rate / original_rate
            new_length = int(len(audio_array) * ratio)
            indices = np.linspace(0, len(audio_array) - 1, new_length)
            return np.interp(indices, np.arange(len(audio_array)), audio_array).astype(
                np.int16
            )

    def _calculate_audio_level(self, audio_data: bytes) -> float:
        """Calculate RMS audio level in dB"""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if len(audio_array) == 0:
                return -60.0

            rms = np.sqrt(np.mean(audio_array.astype(np.float64) ** 2))
            if rms > 0:
                db_level = 20 * np.log10(rms / 32768.0)
                return max(-60.0, db_level)
            else:
                return -60.0
        except Exception:
            return -60.0

    async def _process_audio_frame(self, frame: AudioFrame):
        """Process audio frame through VAD and buffering"""
        try:
            self.stats["total_frames_processed"] += 1

            # Add to audio buffer
            if frame.user_id not in self.audio_buffers:
                self.audio_buffers[frame.user_id] = AudioBuffer(
                    user_id=frame.user_id,
                    max_duration=self.config.audio_buffer_size,
                    sample_rate=self.target_sample_rate,
                )

            buffer = self.audio_buffers[frame.user_id]
            buffer.add_frame(frame)

            # Process through VAD if enabled
            if self.vad:
                vad_result = await self.vad.process_audio_frame(
                    frame.user_id, frame.audio_data, frame.timestamp
                )
                if vad_result:
                    frame.is_speech = vad_result.is_speech
                    frame.confidence = vad_result.confidence

            # Emit audio received event
            await self.event_system.emit(
                EventType.AUDIO_CAPTURED,
                f"Audio frame received from user {frame.user_id}",
                {
                    "user_id": frame.user_id,
                    "duration": frame.duration,
                    "audio_level": frame.audio_level,
                    "is_speech": frame.is_speech,
                    "confidence": frame.confidence,
                },
            )

            # Call callback
            if self.on_audio_received:
                await self.on_audio_received(frame)

        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")

    async def _on_speech_end(
        self, user_id: int, segment: SpeechSegment, audio_file: Optional[Path]
    ):
        """Handle speech end event from VAD"""
        try:
            self.stats["speech_segments_detected"] += 1

            logger.debug(
                f"Speech ended for user {user_id} (duration: {segment.duration:.2f}s)"
            )

            # Use provided audio file or save segment ourselves
            if not audio_file:
                audio_file = await self._save_speech_segment(segment)

            if self.on_speech_completed:
                await self.on_speech_completed(user_id, segment, audio_file)

            await self.event_system.emit(
                EventType.AUDIO_PROCESSED,
                f"Speech segment completed for user {user_id}",
                {
                    "user_id": user_id,
                    "duration": segment.duration,
                    "confidence": segment.average_confidence,
                    "audio_file": str(audio_file) if audio_file else None,
                },
            )

        except Exception as e:
            logger.error(f"Error handling speech end: {e}")

    async def _on_speech_detected(self, user_id: int, vad_result):
        """Handle VAD detection result"""
        # This is called for every frame, so we keep it lightweight

    async def _save_speech_segment(self, segment: SpeechSegment) -> Optional[Path]:
        """Save speech segment to audio file"""
        try:
            if not segment.audio_frames:
                return None

            # Combine all audio frames
            combined_audio = segment.get_combined_audio()
            if not combined_audio:
                return None

            audio_array = np.frombuffer(combined_audio, dtype=np.int16)

            if len(audio_array) == 0:
                return None

            # Generate unique filename
            timestamp = int(segment.start_time)
            # Extract user_id from source_id
            user_id = (
                segment.source_id.replace("discord_user_", "")
                if segment.source_id.startswith("discord_user_")
                else segment.source_id
            )
            filename = f"speech_user_{user_id}_{timestamp}.wav"
            audio_path = TEMP_AUDIO_DIR / filename

            # Save as WAV file
            sf.write(str(audio_path), audio_array, self.target_sample_rate)

            logger.debug(f"Saved speech segment: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Error saving speech segment: {e}")
            return None

    def get_audio_buffer(self, user_id: int) -> Optional[AudioBuffer]:
        """Get audio buffer for a user"""
        return self.audio_buffers.get(user_id)

    def get_recent_audio(self, user_id: int, duration: float = 5.0) -> List[AudioFrame]:
        """Get recent audio frames for a user"""
        buffer = self.get_audio_buffer(user_id)
        if buffer:
            return buffer.get_recent_audio(duration)
        return []

    async def export_user_audio(
        self, user_id: int, duration: float = 30.0
    ) -> Optional[Path]:
        """Export recent audio for a user to file"""
        try:
            frames = self.get_recent_audio(user_id, duration)
            if not frames:
                return None

            # Combine audio frames
            audio_data = []
            for frame in frames:
                audio_array = np.frombuffer(frame.audio_data, dtype=np.int16)
                audio_data.append(audio_array)

            if not audio_data:
                return None

            combined_audio = np.concatenate(audio_data)

            # Generate filename
            timestamp = int(time.time())
            filename = f"export_user_{user_id}_{timestamp}.wav"
            audio_path = TEMP_AUDIO_DIR / filename

            # Save audio file
            sf.write(str(audio_path), combined_audio, self.target_sample_rate)

            logger.info(f"Exported audio for user {user_id}: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Error exporting user audio: {e}")
            return None

    def remove_user(self, user_id: int):
        """Remove user from tracking"""
        # Clean up audio buffer
        self.audio_buffers.pop(user_id, None)

        # Clean up opus decoder
        self.opus_decoders.pop(user_id, None)

        # Clean up VAD tracking
        if self.vad:
            self.vad.remove_user(user_id)

        logger.debug(f"Removed audio tracking for user {user_id}")

    def set_callbacks(self, **callbacks):
        """Set callback functions"""
        for name, callback in callbacks.items():
            if hasattr(self, f"on_{name}"):
                setattr(self, f"on_{name}", callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get receiver statistics"""
        self.stats["active_buffers"] = len(self.audio_buffers)

        # Add VAD stats if available
        vad_stats = {}
        if self.vad:
            vad_stats = self.vad.get_stats()

        # Add voice gateway stats if available
        gateway_stats = {}
        if self.voice_gateway:
            gateway_stats = self.voice_gateway.get_stats()

        return {
            **self.stats,
            "vad": vad_stats,
            "gateway": gateway_stats,
            "target_sample_rate": self.target_sample_rate,
            "target_channels": self.target_channels,
            "frame_size": self.frame_size,
        }

    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_receiving()
        logger.info("Voice receiver cleaned up")

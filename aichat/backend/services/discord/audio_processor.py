"""
Audio Processing and Integration Module

Handles audio processing, transcription integration, and coordination
between Discord audio capture and VtuberMiku's voice processing pipeline.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from .voice_receiver import AudioFrame

try:
    import numpy as np
    import soundfile as sf

    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False
    np = None
    sf = None

from aichat.constants.paths import TEMP_AUDIO_DIR, ensure_dirs
from aichat.core.event_system import EventSeverity, EventType, get_event_system
from ..voice.stt.vad_service import SpeechSegment
from .config import DiscordConfig
from .user_tracker import UserTracker, DiscordUser


logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of audio transcription"""

    user_id: int
    text: str
    confidence: float
    language: Optional[str] = None
    duration: float = 0.0
    audio_file: Optional[Path] = None
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class ProcessingTask:
    """Audio processing task"""

    user_id: int
    audio_file: Path
    segment: SpeechSegment
    priority: int = 1  # Higher number = higher priority
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class AudioProcessor:
    """Processes Discord audio through VtuberMiku's voice pipeline"""

    def __init__(self, config: DiscordConfig, user_tracker: UserTracker):
        self.config = config
        self.user_tracker = user_tracker
        self.event_system = get_event_system()

        # Processing queue
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self.processing_tasks: List[asyncio.Task] = []
        self.active_transcriptions: Dict[int, asyncio.Task] = {}

        # STT Service integration
        self.whisper_service = None
        self.tts_service = None
        self.chat_service = None

        # Callbacks
        self.on_transcription_complete: Optional[Callable] = None
        self.on_user_message: Optional[Callable] = None
        self.on_processing_error: Optional[Callable] = None

        # Statistics
        self.stats = {
            "total_processed": 0,
            "successful_transcriptions": 0,
            "failed_transcriptions": 0,
            "average_processing_time": 0.0,
            "queue_size": 0,
        }

        # Processing settings
        self.max_concurrent_transcriptions = config.max_concurrent_transcriptions
        self.processing_timeout = 30.0  # Timeout for transcription in seconds

        ensure_dirs(TEMP_AUDIO_DIR)
        logger.info("Audio Processor initialized")

    async def start(self):
        """Start audio processing workers"""
        try:
            # Start processing workers
            for i in range(self.max_concurrent_transcriptions):
                task = asyncio.create_task(self._processing_worker(f"worker-{i}"))
                self.processing_tasks.append(task)

            logger.info(
                f"Started {len(self.processing_tasks)} audio processing workers"
            )

        except Exception as e:
            logger.error(f"Error starting audio processor: {e}")

    async def stop(self):
        """Stop audio processing"""
        try:
            # Cancel all processing tasks
            for task in self.processing_tasks:
                task.cancel()

            # Wait for tasks to complete
            if self.processing_tasks:
                await asyncio.gather(*self.processing_tasks, return_exceptions=True)

            # Cancel active transcriptions
            for task in self.active_transcriptions.values():
                task.cancel()

            if self.active_transcriptions:
                await asyncio.gather(
                    *self.active_transcriptions.values(), return_exceptions=True
                )

            self.processing_tasks.clear()
            self.active_transcriptions.clear()

            logger.info("Audio processor stopped")

        except Exception as e:
            logger.error(f"Error stopping audio processor: {e}")

    async def set_services(
        self, whisper_service=None, tts_service=None, chat_service=None
    ):
        """Set VtuberMiku services for integration"""
        self.whisper_service = whisper_service
        self.tts_service = tts_service
        self.chat_service = chat_service

        logger.info("Audio processor services configured")

    async def process_speech_segment(
        self, user_id: int, segment: SpeechSegment, audio_file: Path
    ):
        """Queue speech segment for processing"""
        try:
            if not audio_file or not audio_file.exists():
                logger.warning(f"Audio file not found for user {user_id}: {audio_file}")
                return

            # Check if user has transcription enabled
            user = self.user_tracker.get_user(user_id)
            if not user or not user.recording_enabled:
                logger.debug(f"Transcription disabled for user {user_id}")
                return

            # Create processing task
            task = ProcessingTask(
                user_id=user_id,
                audio_file=audio_file,
                segment=segment,
                priority=self._calculate_priority(user, segment),
            )

            # Add to queue
            await self.processing_queue.put(task)
            self.stats["queue_size"] = self.processing_queue.qsize()

            logger.debug(
                f"Queued speech segment for processing: user {user_id}, duration {segment.duration:.2f}s"
            )

        except Exception as e:
            logger.error(f"Error queuing speech segment: {e}")

    def _calculate_priority(self, user: DiscordUser, segment: SpeechSegment) -> int:
        """Calculate processing priority for a speech segment"""
        priority = 1

        # Higher priority for longer segments
        if segment.duration > 5.0:
            priority += 2
        elif segment.duration > 2.0:
            priority += 1

        # Higher priority for active users
        if user.last_activity and time.time() - user.last_activity < 60:
            priority += 1

        # Higher priority for high confidence segments
        if segment.average_confidence > 0.8:
            priority += 1

        return priority

    async def _processing_worker(self, worker_name: str):
        """Audio processing worker"""
        logger.debug(f"Processing worker {worker_name} started")

        try:
            while True:
                try:
                    # Get next task from queue
                    task = await self.processing_queue.get()
                    self.stats["queue_size"] = self.processing_queue.qsize()

                    # Process the task
                    await self._process_task(task, worker_name)

                    # Mark task as done
                    self.processing_queue.task_done()

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in processing worker {worker_name}: {e}")
                    await asyncio.sleep(1)  # Brief pause before continuing

        except asyncio.CancelledError:
            logger.debug(f"Processing worker {worker_name} cancelled")
        except Exception as e:
            logger.error(f"Processing worker {worker_name} error: {e}")

    async def _process_task(self, task: ProcessingTask, worker_name: str):
        """Process a single audio task"""
        start_time = time.time()

        try:
            logger.debug(
                f"Worker {worker_name} processing audio for user {task.user_id}"
            )

            # Check if user is still tracked
            user = self.user_tracker.get_user(task.user_id)
            if not user:
                logger.debug(f"User {task.user_id} no longer tracked, skipping")
                return

            # Transcribe audio
            transcription = await self._transcribe_audio(task)

            if transcription and transcription.text.strip():
                # Process successful transcription
                await self._handle_transcription_result(transcription)
                self.stats["successful_transcriptions"] += 1
            else:
                logger.debug(f"No transcription result for user {task.user_id}")
                self.stats["failed_transcriptions"] += 1

            # Update statistics
            processing_time = time.time() - start_time
            self.stats["total_processed"] += 1

            # Update average processing time
            total = self.stats["total_processed"]
            current_avg = self.stats["average_processing_time"]
            self.stats["average_processing_time"] = (
                (current_avg * (total - 1)) + processing_time
            ) / total

            # Clean up audio file if configured
            if self.config.cleanup_old_audio:
                try:
                    task.audio_file.unlink(missing_ok=True)
                except Exception as e:
                    logger.debug(f"Error cleaning up audio file: {e}")

        except Exception as e:
            logger.error(f"Error processing task for user {task.user_id}: {e}")
            self.stats["failed_transcriptions"] += 1

            if self.on_processing_error:
                await self.on_processing_error(task.user_id, e)

    async def _transcribe_audio(
        self, task: ProcessingTask
    ) -> Optional[TranscriptionResult]:
        """Transcribe audio using available STT service"""
        try:
            if not task.audio_file.exists():
                logger.warning(f"Audio file not found: {task.audio_file}")
                return None

            # Use Whisper service if available
            if self.whisper_service:
                transcript_data = await self._transcribe_with_whisper(task.audio_file)
                if transcript_data:
                    return TranscriptionResult(
                        user_id=task.user_id,
                        text=transcript_data.get("text", ""),
                        confidence=transcript_data.get("confidence", 0.0),
                        language=transcript_data.get("language"),
                        duration=task.segment.duration,
                        audio_file=task.audio_file,
                    )
            else:
                # Fallback: mock transcription for testing
                logger.debug("Using mock transcription (no Whisper service)")
                return TranscriptionResult(
                    user_id=task.user_id,
                    text=f"Mock transcription for user {task.user_id}",
                    confidence=0.5,
                    duration=task.segment.duration,
                    audio_file=task.audio_file,
                )

            return None

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None

    async def _transcribe_with_whisper(
        self, audio_file: Path
    ) -> Optional[Dict[str, Any]]:
        """Transcribe audio using Whisper service"""
        try:
            if not hasattr(self.whisper_service, "transcribe_file"):
                logger.warning("Whisper service doesn't have transcribe_file method")
                return None

            # Call Whisper service
            result = await self.whisper_service.transcribe_file(str(audio_file))

            if result and isinstance(result, dict):
                return result
            elif result and isinstance(result, str):
                return {"text": result, "confidence": 0.7}
            else:
                logger.debug("No transcription result from Whisper")
                return None

        except Exception as e:
            logger.error(f"Error calling Whisper service: {e}")
            return None

    async def _handle_transcription_result(self, transcription: TranscriptionResult):
        """Handle successful transcription result"""
        try:
            # Get user info
            user = self.user_tracker.get_user(transcription.user_id)
            if not user:
                return

            logger.info(
                f"Transcription completed for {user.display_name}: '{transcription.text}'"
            )

            # Emit transcription event
            await self.event_system.emit(
                EventType.AUDIO_TRANSCRIBED,
                f"Transcribed message from {user.display_name}",
                {
                    "user_id": transcription.user_id,
                    "user_name": user.display_name,
                    "text": transcription.text,
                    "confidence": transcription.confidence,
                    "language": transcription.language,
                    "duration": transcription.duration,
                },
            )

            # Call callback
            if self.on_transcription_complete:
                await self.on_transcription_complete(transcription)

            # Process as user message for chat system
            if self.config.enable_transcription and transcription.confidence > 0.3:
                await self._process_user_message(transcription)

        except Exception as e:
            logger.error(f"Error handling transcription result: {e}")

    async def _process_user_message(self, transcription: TranscriptionResult):
        """Process transcription as user message for chat system"""
        try:
            user = self.user_tracker.get_user(transcription.user_id)
            if not user:
                return

            # Create user message data
            message_data = {
                "user_id": transcription.user_id,
                "user_name": user.display_name,
                "message": transcription.text,
                "source": "discord_voice",
                "timestamp": transcription.timestamp,
                "confidence": transcription.confidence,
                "audio_file": (
                    str(transcription.audio_file) if transcription.audio_file else None
                ),
            }

            # Call user message callback
            if self.on_user_message:
                await self.on_user_message(message_data)

            # Integrate with chat service if available
            if self.chat_service and hasattr(self.chat_service, "process_user_message"):
                try:
                    await self.chat_service.process_user_message(
                        message=transcription.text,
                        user_id=str(transcription.user_id),
                        username=user.display_name,
                        source="discord_voice",
                    )
                except Exception as e:
                    logger.error(f"Error integrating with chat service: {e}")

            logger.debug(
                f"Processed user message from {user.display_name}: {transcription.text}"
            )

        except Exception as e:
            logger.error(f"Error processing user message: {e}")

    async def process_audio_frame(self, frame: "AudioFrame"):
        """Process real-time audio frame (for immediate feedback)"""
        try:
            # This could be used for real-time processing, voice commands, etc.
            # For now, we just track it
            pass

        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")

    def get_queue_status(self) -> Dict[str, Any]:
        """Get processing queue status"""
        return {
            "queue_size": self.processing_queue.qsize(),
            "active_transcriptions": len(self.active_transcriptions),
            "max_concurrent": self.max_concurrent_transcriptions,
            "workers_active": len([t for t in self.processing_tasks if not t.done()]),
        }

    def set_callbacks(self, **callbacks):
        """Set callback functions"""
        for name, callback in callbacks.items():
            if hasattr(self, f"on_{name}"):
                setattr(self, f"on_{name}", callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {**self.stats, "queue_status": self.get_queue_status()}

    async def cleanup(self):
        """Cleanup resources"""
        await self.stop()

        # Clean up old audio files if configured
        if self.config.cleanup_old_audio:
            await self._cleanup_old_audio_files()

        logger.info("Audio processor cleaned up")

    async def _cleanup_old_audio_files(self):
        """Clean up old audio files"""
        try:
            if not TEMP_AUDIO_DIR.exists():
                return

            current_time = time.time()
            max_age = self.config.max_audio_age

            for audio_file in TEMP_AUDIO_DIR.glob("*.wav"):
                try:
                    file_age = current_time - audio_file.stat().st_mtime
                    if file_age > max_age:
                        audio_file.unlink(missing_ok=True)
                        logger.debug(f"Cleaned up old audio file: {audio_file}")
                except Exception as e:
                    logger.debug(f"Error cleaning up audio file {audio_file}: {e}")

        except Exception as e:
            logger.error(f"Error cleaning up old audio files: {e}")


# Convenience class for easy integration
class AudioBuffer:
    """Simple audio buffer for collecting frames"""

    def __init__(self, max_duration: float = 10.0):
        self.max_duration = max_duration
        self.frames: List["AudioFrame"] = []
        self.total_duration = 0.0

    def add_frame(self, frame: "AudioFrame"):
        """Add audio frame to buffer"""
        self.frames.append(frame)
        self.total_duration += frame.duration

        # Remove old frames if buffer is too large
        while self.total_duration > self.max_duration and self.frames:
            old_frame = self.frames.pop(0)
            self.total_duration -= old_frame.duration

    def get_combined_audio(self) -> Optional[bytes]:
        """Get combined audio data from all frames"""
        if not self.frames:
            return None

        try:
            audio_data = []
            for frame in self.frames:
                audio_array = np.frombuffer(frame.audio_data, dtype=np.int16)
                audio_data.append(audio_array)

            if audio_data:
                return np.concatenate(audio_data).tobytes()

        except Exception as e:
            logger.error(f"Error combining audio data: {e}")

        return None

    def clear(self):
        """Clear the buffer"""
        self.frames.clear()
        self.total_duration = 0.0

    def get_duration(self) -> float:
        """Get total duration of buffered audio"""
        return self.total_duration

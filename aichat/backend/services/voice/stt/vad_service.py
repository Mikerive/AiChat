"""
Voice Activity Detection (VAD) Service

A universal VAD service that can be used by any IO service (Discord, microphone input,
file processing, etc.) to detect speech activity in audio streams.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path

import numpy as np

try:
    import webrtcvad

    WEBRTC_VAD_AVAILABLE = True
except ImportError:
    WEBRTC_VAD_AVAILABLE = False
    webrtcvad = None

try:
    import soundfile as sf

    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None

try:
    from models import settings_dao, vad_model

    from aichat.constants.paths import TEMP_AUDIO_DIR, ensure_dirs
    from aichat.core.event_system import EventSeverity, EventType, get_event_system
except ImportError:
    # Set fallback values when models are not available
    settings_dao = None
    vad_model = None

logger = logging.getLogger(__name__)

# Import VADSensitivityPreset from constants, keep legacy enum for compatibility
try:
    from constants.vad_constants import VADSensitivityPreset
except ImportError:

    class VADSensitivityPreset:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"


class VADSensitivity(Enum):
    """Voice Activity Detection sensitivity levels (legacy compatibility)"""

    LOW = 0  # Less sensitive, fewer false positives
    MEDIUM = 1  # Balanced
    HIGH = 2  # More sensitive, catches quiet speech


class VADState(Enum):
    """Voice activity detection states"""

    SILENCE = "silence"
    SPEECH = "speech"
    TRANSITION = "transition"


@dataclass
class VADConfig:
    """Voice Activity Detection configuration"""

    # Core VAD settings
    sensitivity: VADSensitivity = VADSensitivity.MEDIUM
    sample_rate: int = 16000
    frame_duration_ms: int = 20  # 20ms frames for WebRTC VAD

    # Speech detection thresholds
    min_speech_duration: float = 0.3  # Minimum speech duration in seconds
    max_silence_duration: float = 1.0  # Maximum silence before ending speech

    # Energy-based fallback settings (when WebRTC VAD unavailable)
    energy_threshold_db: float = -40.0  # dB threshold for energy-based detection

    # Processing settings
    enable_preprocessing: bool = True
    enable_noise_suppression: bool = True
    enable_audio_enhancement: bool = False

    # Buffer settings
    audio_buffer_duration: float = 10.0  # Seconds of audio to buffer per source
    max_sources: int = 50  # Maximum number of audio sources to track

    # Output settings
    save_speech_segments: bool = True
    segment_output_dir: Optional[Path] = None

    def __post_init__(self):
        if self.segment_output_dir is None:
            self.segment_output_dir = TEMP_AUDIO_DIR / "vad_segments"

        # Calculate frame size in samples
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)

        # Calculate frame counts for thresholds
        self.min_speech_frames = int(
            self.min_speech_duration * 1000 / self.frame_duration_ms
        )
        self.max_silence_frames = int(
            self.max_silence_duration * 1000 / self.frame_duration_ms
        )


@dataclass
class VADResult:
    """Voice activity detection result"""

    source_id: str  # Unique identifier for audio source (user_id, device_id, etc.)
    timestamp: float
    is_speech: bool
    confidence: float
    audio_level_db: float
    state: VADState
    frame_data: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "source_id": self.source_id,
            "timestamp": self.timestamp,
            "is_speech": self.is_speech,
            "confidence": self.confidence,
            "audio_level_db": self.audio_level_db,
            "state": self.state.value,
        }


@dataclass
class SpeechSegment:
    """Represents a detected speech segment"""

    source_id: str
    start_time: float
    end_time: Optional[float] = None
    audio_frames: List[bytes] = field(default_factory=list)
    confidence_scores: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Get duration of speech segment"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def average_confidence(self) -> float:
        """Get average confidence score"""
        if self.confidence_scores:
            return sum(self.confidence_scores) / len(self.confidence_scores)
        return 0.0

    def add_frame(self, audio_data: bytes, confidence: float):
        """Add audio frame to segment"""
        self.audio_frames.append(audio_data)
        self.confidence_scores.append(confidence)

    def finalize(self, end_time: Optional[float] = None):
        """Finalize the speech segment"""
        self.end_time = end_time or time.time()

    def get_combined_audio(self) -> Optional[bytes]:
        """Get combined audio data from all frames"""
        if not self.audio_frames:
            return None
        return b"".join(self.audio_frames)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "source_id": self.source_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "average_confidence": self.average_confidence,
            "frame_count": len(self.audio_frames),
            "metadata": self.metadata,
        }


class AudioSourceTracker:
    """Tracks VAD state for a single audio source"""

    def __init__(self, source_id: str, config: VADConfig):
        self.source_id = source_id
        self.config = config

        # State tracking
        self.current_state = VADState.SILENCE
        self.speech_frame_count = 0
        self.silence_frame_count = 0

        # Current speech segment
        self.current_segment: Optional[SpeechSegment] = None

        # Audio buffer for lookback
        self.audio_buffer: deque = deque(maxlen=100)  # Keep last 100 frames

        # Statistics
        self.total_frames_processed = 0
        self.total_speech_frames = 0
        self.total_segments = 0
        self.last_activity = time.time()

    def process_frame(
        self, audio_data: bytes, is_speech: bool, confidence: float, timestamp: float
    ) -> Optional[SpeechSegment]:
        """Process an audio frame and return completed speech segment if any"""
        self.total_frames_processed += 1
        self.last_activity = timestamp

        # Add to buffer
        self.audio_buffer.append((timestamp, audio_data, confidence))

        # Update frame counters
        if is_speech:
            self.speech_frame_count += 1
            self.silence_frame_count = 0
            self.total_speech_frames += 1
        else:
            self.silence_frame_count += 1
            self.speech_frame_count = 0

        completed_segment = None

        # State machine logic
        if self.current_state == VADState.SILENCE:
            if self.speech_frame_count >= self.config.min_speech_frames:
                # Start new speech segment
                completed_segment = self._start_speech_segment(timestamp)

        elif self.current_state == VADState.SPEECH:
            if self.silence_frame_count >= self.config.max_silence_frames:
                # End current speech segment
                completed_segment = self._end_speech_segment(timestamp)

        # Add current frame to active segment
        if self.current_state == VADState.SPEECH and self.current_segment:
            self.current_segment.add_frame(audio_data, confidence)

        return completed_segment

    def _start_speech_segment(self, timestamp: float) -> Optional[SpeechSegment]:
        """Start a new speech segment"""
        self.current_state = VADState.SPEECH
        self.current_segment = SpeechSegment(
            source_id=self.source_id, start_time=timestamp
        )

        # Add buffered audio for lookback
        lookback_duration = 0.5  # 500ms lookback
        for frame_timestamp, audio_data, confidence in self.audio_buffer:
            if timestamp - frame_timestamp <= lookback_duration:
                self.current_segment.add_frame(audio_data, confidence)

        logger.debug(f"Started speech segment for source {self.source_id}")
        return None  # Don't return segment until it's complete

    def _end_speech_segment(self, timestamp: float) -> Optional[SpeechSegment]:
        """End current speech segment"""
        if not self.current_segment:
            return None

        self.current_state = VADState.SILENCE
        self.current_segment.finalize(timestamp)
        self.total_segments += 1

        completed_segment = self.current_segment
        self.current_segment = None

        logger.debug(
            f"Ended speech segment for source {self.source_id} (duration: {completed_segment.duration:.2f}s)"
        )
        return completed_segment

    def force_end_segment(self) -> Optional[SpeechSegment]:
        """Force end current speech segment (e.g., when source disconnects)"""
        if self.current_segment:
            return self._end_speech_segment(time.time())
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for this source"""
        return {
            "source_id": self.source_id,
            "current_state": self.current_state.value,
            "total_frames_processed": self.total_frames_processed,
            "total_speech_frames": self.total_speech_frames,
            "total_segments": self.total_segments,
            "speech_ratio": self.total_speech_frames
            / max(1, self.total_frames_processed),
            "last_activity": self.last_activity,
            "has_active_segment": self.current_segment is not None,
        }


class VADService:
    """Universal Voice Activity Detection Service"""

    def __init__(self, config: Optional[VADConfig] = None):
        self.config = config or VADConfig()
        self.event_system = get_event_system()

        # WebRTC VAD engine
        self.webrtc_vad = None
        self._init_webrtc_vad()

        # Source tracking
        self.sources: Dict[str, AudioSourceTracker] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None
        self.on_vad_result: Optional[Callable] = None

        # Statistics
        self.stats = {
            "total_sources": 0,
            "active_sources": 0,
            "total_frames_processed": 0,
            "total_speech_segments": 0,
            "webrtc_available": WEBRTC_VAD_AVAILABLE,
        }

        # Ensure output directory exists
        ensure_dirs(self.config.segment_output_dir)

        logger.info(
            f"VAD Service initialized (WebRTC available: {WEBRTC_VAD_AVAILABLE})"
        )

    def _init_webrtc_vad(self):
        """Initialize WebRTC VAD if available"""
        if WEBRTC_VAD_AVAILABLE:
            try:
                self.webrtc_vad = webrtcvad.Vad()
                # Set aggressiveness (0-3, where 3 is most aggressive)
                aggressiveness = {
                    VADSensitivity.LOW: 3,  # Most aggressive (fewer false positives)
                    VADSensitivity.MEDIUM: 2,  # Moderate
                    VADSensitivity.HIGH: 1,  # Less aggressive (catches quiet speech)
                }.get(self.config.sensitivity, 2)

                self.webrtc_vad.set_mode(aggressiveness)
                logger.info(
                    f"WebRTC VAD initialized with aggressiveness: {aggressiveness}"
                )

            except Exception as e:
                logger.error(f"Failed to initialize WebRTC VAD: {e}")
                self.webrtc_vad = None
        else:
            logger.warning(
                "WebRTC VAD not available. Install with: pip install webrtcvad"
            )

    async def start(self):
        """Start the VAD service"""
        try:
            # Start cleanup task for inactive sources
            self._cleanup_task = asyncio.create_task(self._cleanup_inactive_sources())

            await self.event_system.emit(
                EventType.AUDIO_PROCESSED,
                "VAD Service started",
                {"service": "vad", "webrtc_available": WEBRTC_VAD_AVAILABLE},
            )

            logger.info("VAD Service started")

        except Exception as e:
            logger.error(f"Error starting VAD service: {e}")
            raise

    async def stop(self):
        """Stop the VAD service"""
        try:
            # Cancel cleanup task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # End all active speech segments
            for source in self.sources.values():
                segment = source.force_end_segment()
                if segment:
                    await self._handle_speech_end(segment)

            # Clear sources
            self.sources.clear()

            await self.event_system.emit(
                EventType.AUDIO_PROCESSED, "VAD Service stopped", {"service": "vad"}
            )

            logger.info("VAD Service stopped")

        except Exception as e:
            logger.error(f"Error stopping VAD service: {e}")

    async def process_audio_frame(
        self, source_id: str, audio_data: bytes, timestamp: Optional[float] = None
    ) -> VADResult:
        """Process an audio frame for voice activity detection"""
        if timestamp is None:
            timestamp = time.time()

        try:
            # Ensure source is tracked
            if source_id not in self.sources:
                self._add_source(source_id)

            source = self.sources[source_id]

            # Convert audio data to numpy array for analysis
            audio_array = self._bytes_to_numpy(audio_data)

            # Calculate audio level
            audio_level_db = self._calculate_audio_level(audio_array)

            # Perform VAD detection
            is_speech, confidence = await self._detect_voice_activity(
                audio_data, audio_level_db
            )

            # Process through source tracker
            completed_segment = source.process_frame(
                audio_data, is_speech, confidence, timestamp
            )

            # Handle completed speech segment
            if completed_segment:
                await self._handle_speech_end(completed_segment)

            # Create result
            result = VADResult(
                source_id=source_id,
                timestamp=timestamp,
                is_speech=is_speech,
                confidence=confidence,
                audio_level_db=audio_level_db,
                state=source.current_state,
                frame_data=audio_data if self.config.save_speech_segments else None,
            )

            # Update statistics
            self.stats["total_frames_processed"] += 1
            self.stats["active_sources"] = len(
                [s for s in self.sources.values() if s.current_state == VADState.SPEECH]
            )

            # Emit event
            await self.event_system.emit(
                EventType.AUDIO_CAPTURED,
                f"VAD processed frame for source {source_id}",
                result.to_dict(),
            )

            # Call callback
            if self.on_vad_result:
                await self.on_vad_result(result)

            return result

        except Exception as e:
            logger.error(f"Error processing audio frame for source {source_id}: {e}")
            # Return safe default result
            return VADResult(
                source_id=source_id,
                timestamp=timestamp,
                is_speech=False,
                confidence=0.0,
                audio_level_db=-60.0,
                state=VADState.SILENCE,
            )

    def _add_source(self, source_id: str):
        """Add a new audio source for tracking"""
        if len(self.sources) >= self.config.max_sources:
            # Remove oldest inactive source
            self._remove_oldest_inactive_source()

        self.sources[source_id] = AudioSourceTracker(source_id, self.config)
        self.stats["total_sources"] += 1

        logger.debug(f"Added VAD tracking for source: {source_id}")

    def _remove_oldest_inactive_source(self):
        """Remove the oldest inactive source"""
        inactive_sources = [
            (sid, source)
            for sid, source in self.sources.items()
            if source.current_state == VADState.SILENCE
        ]

        if inactive_sources:
            # Find oldest by last activity
            oldest_sid, oldest_source = min(
                inactive_sources, key=lambda x: x[1].last_activity
            )

            # Force end any active segment
            segment = oldest_source.force_end_segment()
            if segment:
                asyncio.create_task(self._handle_speech_end(segment))

            del self.sources[oldest_sid]
            logger.debug(f"Removed oldest inactive source: {oldest_sid}")

    def _bytes_to_numpy(self, audio_data: bytes) -> np.ndarray:
        """Convert audio bytes to numpy array"""
        try:
            return np.frombuffer(audio_data, dtype=np.int16)
        except Exception as e:
            logger.debug(f"Error converting audio bytes: {e}")
            return np.array([], dtype=np.int16)

    def _calculate_audio_level(self, audio_array: np.ndarray) -> float:
        """Calculate RMS audio level in dB"""
        try:
            if len(audio_array) == 0:
                return -60.0

            # Calculate RMS
            rms = np.sqrt(np.mean(audio_array.astype(np.float64) ** 2))

            # Convert to dB
            if rms > 0:
                db_level = 20 * np.log10(rms / 32768.0)  # Normalize to 16-bit range
                return max(-60.0, db_level)  # Clamp minimum to -60dB
            else:
                return -60.0

        except Exception as e:
            logger.debug(f"Error calculating audio level: {e}")
            return -60.0

    async def _detect_voice_activity(
        self, audio_data: bytes, audio_level_db: float
    ) -> Tuple[bool, float]:
        """Detect voice activity using available methods"""
        is_speech = False
        confidence = 0.0

        # Method 1: WebRTC VAD (most reliable)
        if (
            self.webrtc_vad and len(audio_data) == self.config.frame_size * 2
        ):  # 16-bit samples
            try:
                webrtc_result = self.webrtc_vad.is_speech(
                    audio_data, self.config.sample_rate
                )
                is_speech = webrtc_result
                confidence = 0.8 if webrtc_result else 0.2
            except Exception as e:
                logger.debug(f"WebRTC VAD error: {e}")

        # Method 2: Energy-based detection (fallback)
        if not self.webrtc_vad:
            is_speech = audio_level_db > self.config.energy_threshold_db
            # Normalize confidence based on audio level
            confidence = min(
                1.0, max(0.0, (audio_level_db + 60) / 20)
            )  # Normalize -60dB to 0dB range

        return is_speech, confidence

    async def _handle_speech_end(self, segment: SpeechSegment):
        """Handle completed speech segment"""
        try:
            self.stats["total_speech_segments"] += 1

            logger.debug(
                f"Speech segment completed for source {segment.source_id} "
                f"(duration: {segment.duration:.2f}s, confidence: {segment.average_confidence:.2f})"
            )

            # Save segment to file if configured
            audio_file = None
            if self.config.save_speech_segments:
                audio_file = await self._save_speech_segment(segment)

            # Emit event
            await self.event_system.emit(
                EventType.AUDIO_PROCESSED,
                f"Speech segment completed for source {segment.source_id}",
                {
                    **segment.to_dict(),
                    "audio_file": str(audio_file) if audio_file else None,
                },
            )

            # Call callback
            if self.on_speech_end:
                await self.on_speech_end(segment, audio_file)

        except Exception as e:
            logger.error(f"Error handling speech end: {e}")

    async def _save_speech_segment(self, segment: SpeechSegment) -> Optional[Path]:
        """Save speech segment to audio file"""
        try:
            if not SOUNDFILE_AVAILABLE:
                logger.debug("soundfile not available, cannot save speech segment")
                return None

            audio_data = segment.get_combined_audio()
            if not audio_data:
                return None

            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if len(audio_array) == 0:
                return None

            # Generate unique filename
            timestamp = int(segment.start_time)
            filename = f"speech_{segment.source_id}_{timestamp}.wav"
            audio_path = self.config.segment_output_dir / filename

            # Ensure directory exists
            audio_path.parent.mkdir(parents=True, exist_ok=True)

            # Save as WAV file
            sf.write(str(audio_path), audio_array, self.config.sample_rate)

            logger.debug(f"Saved speech segment: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Error saving speech segment: {e}")
            return None

    async def _cleanup_inactive_sources(self):
        """Periodically clean up inactive sources"""
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute

                current_time = time.time()
                inactive_threshold = 300  # 5 minutes

                sources_to_remove = []
                for source_id, source in self.sources.items():
                    if (
                        current_time - source.last_activity > inactive_threshold
                        and source.current_state == VADState.SILENCE
                    ):
                        sources_to_remove.append(source_id)

                for source_id in sources_to_remove:
                    self.remove_source(source_id)

        except asyncio.CancelledError:
            logger.debug("VAD cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in VAD cleanup task: {e}")

    def remove_source(self, source_id: str) -> Optional[SpeechSegment]:
        """Remove a source from tracking"""
        if source_id not in self.sources:
            return None

        source = self.sources[source_id]

        # Force end any active segment
        completed_segment = source.force_end_segment()
        if completed_segment:
            asyncio.create_task(self._handle_speech_end(completed_segment))

        del self.sources[source_id]
        logger.debug(f"Removed VAD tracking for source: {source_id}")

        return completed_segment

    def get_source_state(self, source_id: str) -> Optional[VADState]:
        """Get current VAD state for a source"""
        source = self.sources.get(source_id)
        return source.current_state if source else None

    def get_active_sources(self) -> List[str]:
        """Get list of sources currently speaking"""
        return [
            source_id
            for source_id, source in self.sources.items()
            if source.current_state == VADState.SPEECH
        ]

    def get_source_stats(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific source"""
        source = self.sources.get(source_id)
        return source.get_stats() if source else None

    def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive VAD statistics"""
        source_stats = {
            source_id: source.get_stats() for source_id, source in self.sources.items()
        }

        return {
            **self.stats,
            "sources": source_stats,
            "config": {
                "sensitivity": self.config.sensitivity.value,
                "sample_rate": self.config.sample_rate,
                "frame_duration_ms": self.config.frame_duration_ms,
                "min_speech_duration": self.config.min_speech_duration,
                "max_silence_duration": self.config.max_silence_duration,
            },
        }

    def set_callbacks(self, **callbacks):
        """Set callback functions"""
        for name, callback in callbacks.items():
            if hasattr(self, f"on_{name}"):
                setattr(self, f"on_{name}", callback)

    async def cleanup(self):
        """Cleanup VAD service resources"""
        await self.stop()
        logger.info("VAD Service cleaned up")

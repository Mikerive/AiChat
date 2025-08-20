"""
AudioIO Service for centralized audio input/output device management
"""

import logging
import asyncio
import time
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np
import soundfile as sf

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants.paths import TEMP_AUDIO_DIR, AUDIO_OUTPUT, ensure_dirs

try:
    from event_system import get_event_system, EventType, EventSeverity
except ImportError:
    # Fallback for when imports aren't available
    def get_event_system():
        class MockEventSystem:
            async def emit(self, *args, **kwargs):
                pass
        return MockEventSystem()
    
    class EventType:
        AUDIO_DEVICE_CHANGED = "audio_device_changed"
        AUDIO_CAPTURED = "audio_captured"
        AUDIO_PLAYED = "audio_played"
        AUDIO_GENERATED = "audio_generated"
        ERROR_OCCURRED = "error_occurred"
    
    class EventSeverity:
        ERROR = "error"

logger = logging.getLogger(__name__)


class AudioFormat(Enum):
    """Supported audio formats"""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"


class DeviceType(Enum):
    """Audio device types"""
    INPUT = "input"
    OUTPUT = "output"


@dataclass
class AudioDevice:
    """Audio device information"""
    id: int
    name: str
    device_type: DeviceType
    channels: int
    sample_rate: int
    is_default: bool = False
    is_available: bool = True


@dataclass
class AudioConfig:
    """Audio configuration settings"""
    sample_rate: int = 16000
    channels: int = 1
    format: AudioFormat = AudioFormat.WAV
    chunk_size: int = 1024
    input_device_id: Optional[int] = None
    output_device_id: Optional[int] = None
    volume: float = 1.0
    noise_suppression: bool = True
    auto_gain_control: bool = True


class AudioIOService:
    """Service for centralized audio input/output management"""
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self.event_system = get_event_system()
        self._input_devices: List[AudioDevice] = []
        self._output_devices: List[AudioDevice] = []
        self._current_input_device: Optional[AudioDevice] = None
        self._current_output_device: Optional[AudioDevice] = None
        self._recording_active = False
        self._playback_active = False
        
        # Initialize directories
        ensure_dirs(TEMP_AUDIO_DIR, AUDIO_OUTPUT)
        
        # Try to initialize audio backends
        self._initialize_audio_backends()
        
        logger.info("AudioIO Service initialized")

    def _initialize_audio_backends(self):
        """Initialize available audio backends"""
        try:
            # Try to import and initialize PyAudio for device management
            self._init_pyaudio()
        except ImportError:
            logger.warning("PyAudio not available. Using mock audio devices.")
            self._init_mock_devices()
        except Exception as e:
            logger.error(f"Error initializing audio backends: {e}")
            self._init_mock_devices()

    def _init_pyaudio(self):
        """Initialize PyAudio backend"""
        try:
            import pyaudio
            self._pyaudio = pyaudio.PyAudio()
            self._refresh_devices()
            logger.info("PyAudio backend initialized successfully")
        except Exception as e:
            logger.warning(f"PyAudio initialization failed: {e}")
            self._pyaudio = None
            self._init_mock_devices()

    def _init_mock_devices(self):
        """Initialize mock audio devices for testing"""
        self._input_devices = [
            AudioDevice(
                id=0,
                name="Default Microphone",
                device_type=DeviceType.INPUT,
                channels=1,
                sample_rate=16000,
                is_default=True
            ),
            AudioDevice(
                id=1,
                name="USB Microphone",
                device_type=DeviceType.INPUT,
                channels=2,
                sample_rate=44100
            )
        ]
        
        self._output_devices = [
            AudioDevice(
                id=0,
                name="Default Speakers",
                device_type=DeviceType.OUTPUT,
                channels=2,
                sample_rate=44100,
                is_default=True
            ),
            AudioDevice(
                id=1,
                name="Headphones",
                device_type=DeviceType.OUTPUT,
                channels=2,
                sample_rate=48000
            )
        ]
        
        # Set default devices
        self._current_input_device = self._input_devices[0]
        self._current_output_device = self._output_devices[0]
        
        logger.info("Mock audio devices initialized")

    def _refresh_devices(self):
        """Refresh available audio devices using PyAudio"""
        if not hasattr(self, '_pyaudio') or self._pyaudio is None:
            return
        
        try:
            self._input_devices.clear()
            self._output_devices.clear()
            
            # Get device info from PyAudio
            device_count = self._pyaudio.get_device_count()
            default_input = self._pyaudio.get_default_input_device_info()
            default_output = self._pyaudio.get_default_output_device_info()
            
            for i in range(device_count):
                try:
                    device_info = self._pyaudio.get_device_info_by_index(i)
                    
                    # Input devices
                    if device_info['maxInputChannels'] > 0:
                        device = AudioDevice(
                            id=i,
                            name=device_info['name'],
                            device_type=DeviceType.INPUT,
                            channels=device_info['maxInputChannels'],
                            sample_rate=int(device_info['defaultSampleRate']),
                            is_default=(i == default_input['index'])
                        )
                        self._input_devices.append(device)
                        
                        if device.is_default:
                            self._current_input_device = device
                    
                    # Output devices
                    if device_info['maxOutputChannels'] > 0:
                        device = AudioDevice(
                            id=i,
                            name=device_info['name'],
                            device_type=DeviceType.OUTPUT,
                            channels=device_info['maxOutputChannels'],
                            sample_rate=int(device_info['defaultSampleRate']),
                            is_default=(i == default_output['index'])
                        )
                        self._output_devices.append(device)
                        
                        if device.is_default:
                            self._current_output_device = device
                            
                except Exception as e:
                    logger.warning(f"Error reading device {i}: {e}")
                    continue
            
            logger.info(f"Refreshed devices: {len(self._input_devices)} input, {len(self._output_devices)} output")
            
        except Exception as e:
            logger.error(f"Error refreshing devices: {e}")

    async def get_input_devices(self) -> List[AudioDevice]:
        """Get available input devices"""
        return self._input_devices.copy()

    async def get_output_devices(self) -> List[AudioDevice]:
        """Get available output devices"""
        return self._output_devices.copy()

    async def set_input_device(self, device_id: int) -> bool:
        """Set the current input device"""
        try:
            device = next((d for d in self._input_devices if d.id == device_id), None)
            if not device:
                logger.error(f"Input device not found: {device_id}")
                return False
            
            self._current_input_device = device
            self.config.input_device_id = device_id
            
            await self.event_system.emit(
                EventType.AUDIO_DEVICE_CHANGED,
                f"Input device changed to: {device.name}",
                {
                    "device_type": "input",
                    "device_id": device_id,
                    "device_name": device.name
                }
            )
            
            logger.info(f"Input device set to: {device.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting input device: {e}")
            return False

    async def set_output_device(self, device_id: int) -> bool:
        """Set the current output device"""
        try:
            device = next((d for d in self._output_devices if d.id == device_id), None)
            if not device:
                logger.error(f"Output device not found: {device_id}")
                return False
            
            self._current_output_device = device
            self.config.output_device_id = device_id
            
            await self.event_system.emit(
                EventType.AUDIO_DEVICE_CHANGED,
                f"Output device changed to: {device.name}",
                {
                    "device_type": "output",
                    "device_id": device_id,
                    "device_name": device.name
                }
            )
            
            logger.info(f"Output device set to: {device.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting output device: {e}")
            return False

    async def record_audio(
        self,
        duration: float,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """Record audio from the current input device"""
        try:
            if self._recording_active:
                logger.warning("Recording already in progress")
                return None
            
            # Generate output path if not provided
            if output_path is None:
                timestamp = int(time.time())
                output_path = TEMP_AUDIO_DIR / f"recording_{timestamp}.wav"
            
            self._recording_active = True
            
            await self.event_system.emit(
                EventType.AUDIO_CAPTURED,
                f"Started audio recording for {duration}s",
                {
                    "duration": duration,
                    "output_path": str(output_path),
                    "device": self._current_input_device.name if self._current_input_device else "unknown"
                }
            )
            
            # Record audio (implementation depends on backend)
            if hasattr(self, '_pyaudio') and self._pyaudio is not None:
                success = await self._record_with_pyaudio(duration, output_path)
            else:
                success = await self._record_mock_audio(duration, output_path)
            
            self._recording_active = False
            
            if success and output_path.exists():
                await self.event_system.emit(
                    EventType.AUDIO_CAPTURED,
                    f"Audio recording completed: {output_path.name}",
                    {
                        "duration": duration,
                        "output_path": str(output_path),
                        "file_size": output_path.stat().st_size
                    }
                )
                return output_path
            else:
                logger.error("Audio recording failed")
                return None
            
        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            self._recording_active = False
            
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"Audio recording failed: {e}",
                {"duration": duration},
                EventSeverity.ERROR
            )
            
            return None

    async def _record_with_pyaudio(self, duration: float, output_path: Path) -> bool:
        """Record audio using PyAudio"""
        try:
            if not self._current_input_device:
                logger.error("No input device selected")
                return False
            
            # Audio recording parameters
            sample_rate = self.config.sample_rate
            channels = self.config.channels
            chunk_size = self.config.chunk_size
            
            # Open audio stream
            stream = self._pyaudio.open(
                format=self._pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=self._current_input_device.id,
                frames_per_buffer=chunk_size
            )
            
            frames = []
            num_chunks = int(sample_rate * duration / chunk_size)
            
            logger.info(f"Recording {duration}s of audio...")
            
            for _ in range(num_chunks):
                if not self._recording_active:
                    break
                data = stream.read(chunk_size)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            # Save audio data
            audio_data = b''.join(frames)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Normalize to float32
            audio_array = audio_array.astype(np.float32) / 32768.0
            
            # Save as WAV file
            sf.write(str(output_path), audio_array, sample_rate)
            
            logger.info(f"Audio saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error in PyAudio recording: {e}")
            return False

    async def _record_mock_audio(self, duration: float, output_path: Path) -> bool:
        """Create mock audio recording for testing"""
        try:
            # Generate silent audio
            sample_rate = self.config.sample_rate
            samples = int(sample_rate * duration)
            audio_data = np.zeros(samples, dtype=np.float32)
            
            # Add some mock audio content (sine wave)
            t = np.linspace(0, duration, samples)
            audio_data = 0.1 * np.sin(2 * np.pi * 440 * t)  # 440Hz tone
            
            # Save audio
            sf.write(str(output_path), audio_data, sample_rate)
            
            logger.info(f"Mock audio saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating mock audio: {e}")
            return False

    async def play_audio(self, audio_path: Union[str, Path]) -> bool:
        """Play audio file through the current output device"""
        try:
            audio_path = Path(audio_path)
            
            if not audio_path.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return False
            
            if self._playback_active:
                logger.warning("Playback already in progress")
                return False
            
            self._playback_active = True
            
            await self.event_system.emit(
                EventType.AUDIO_PLAYED,
                f"Started audio playback: {audio_path.name}",
                {
                    "audio_path": str(audio_path),
                    "device": self._current_output_device.name if self._current_output_device else "unknown"
                }
            )
            
            # Play audio (implementation depends on backend)
            if hasattr(self, '_pyaudio') and self._pyaudio is not None:
                success = await self._play_with_pyaudio(audio_path)
            else:
                success = await self._play_mock_audio(audio_path)
            
            self._playback_active = False
            
            if success:
                await self.event_system.emit(
                    EventType.AUDIO_PLAYED,
                    f"Audio playback completed: {audio_path.name}",
                    {"audio_path": str(audio_path)}
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            self._playback_active = False
            
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"Audio playback failed: {e}",
                {"audio_path": str(audio_path)},
                EventSeverity.ERROR
            )
            
            return False

    async def _play_with_pyaudio(self, audio_path: Path) -> bool:
        """Play audio using PyAudio"""
        try:
            if not self._current_output_device:
                logger.error("No output device selected")
                return False
            
            # Load audio file
            audio_data, sample_rate = sf.read(str(audio_path))
            
            # Convert to int16 for PyAudio
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # Handle mono/stereo
            if len(audio_data.shape) == 1:
                channels = 1
            else:
                channels = audio_data.shape[1]
            
            # Open audio stream
            stream = self._pyaudio.open(
                format=self._pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                output=True,
                output_device_index=self._current_output_device.id
            )
            
            # Play audio
            chunk_size = self.config.chunk_size
            audio_bytes = audio_data.tobytes()
            
            for i in range(0, len(audio_bytes), chunk_size * 2 * channels):
                if not self._playback_active:
                    break
                chunk = audio_bytes[i:i + chunk_size * 2 * channels]
                stream.write(chunk)
            
            stream.stop_stream()
            stream.close()
            
            logger.info(f"Audio playback completed: {audio_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error in PyAudio playback: {e}")
            return False

    async def _play_mock_audio(self, audio_path: Path) -> bool:
        """Mock audio playback for testing"""
        try:
            # Simulate playback delay
            audio_data, sample_rate = sf.read(str(audio_path))
            duration = len(audio_data) / sample_rate
            
            logger.info(f"Mock playing audio for {duration:.2f}s: {audio_path}")
            await asyncio.sleep(min(duration, 5.0))  # Cap at 5s for testing
            
            return True
            
        except Exception as e:
            logger.error(f"Error in mock playback: {e}")
            return False

    async def stop_recording(self):
        """Stop current recording"""
        if self._recording_active:
            self._recording_active = False
            logger.info("Recording stopped")

    async def stop_playback(self):
        """Stop current playback"""
        if self._playback_active:
            self._playback_active = False
            logger.info("Playback stopped")

    async def set_volume(self, volume: float) -> bool:
        """Set output volume (0.0 to 1.0)"""
        try:
            volume = max(0.0, min(1.0, volume))
            self.config.volume = volume
            
            await self.event_system.emit(
                EventType.AUDIO_DEVICE_CHANGED,
                f"Volume set to {volume * 100:.0f}%",
                {"volume": volume}
            )
            
            logger.info(f"Volume set to {volume * 100:.0f}%")
            return True
            
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False

    async def normalize_audio_format(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Path] = None,
        target_format: AudioFormat = AudioFormat.WAV,
        target_sample_rate: Optional[int] = None,
        target_channels: Optional[int] = None
    ) -> Optional[Path]:
        """Normalize audio file to specified format and parameters"""
        try:
            input_path = Path(input_path)
            
            if output_path is None:
                output_path = TEMP_AUDIO_DIR / f"normalized_{int(time.time())}.{target_format.value}"
            
            # Load audio
            audio_data, sample_rate = sf.read(str(input_path))
            
            # Resample if needed
            if target_sample_rate and target_sample_rate != sample_rate:
                import librosa
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=target_sample_rate)
                sample_rate = target_sample_rate
            
            # Convert channels if needed
            if target_channels:
                if len(audio_data.shape) == 1 and target_channels == 2:
                    # Mono to stereo
                    audio_data = np.column_stack((audio_data, audio_data))
                elif len(audio_data.shape) == 2 and target_channels == 1:
                    # Stereo to mono
                    audio_data = np.mean(audio_data, axis=1)
            
            # Save normalized audio
            sf.write(str(output_path), audio_data, sample_rate)
            
            logger.info(f"Audio normalized: {input_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error normalizing audio: {e}")
            return None

    async def get_audio_info(self, audio_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """Get audio file information"""
        try:
            audio_path = Path(audio_path)
            
            if not audio_path.exists():
                return None
            
            # Load audio file
            audio_data, sample_rate = sf.read(str(audio_path))
            
            # Calculate properties
            duration = len(audio_data) / sample_rate
            channels = 1 if len(audio_data.shape) == 1 else audio_data.shape[1]
            file_size = audio_path.stat().st_size
            
            return {
                "file_path": str(audio_path),
                "file_size": file_size,
                "duration": duration,
                "sample_rate": sample_rate,
                "channels": channels,
                "format": audio_path.suffix.lower().replace('.', ''),
                "samples": len(audio_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting audio info: {e}")
            return None

    async def get_service_status(self) -> Dict[str, Any]:
        """Get audio service status"""
        try:
            return {
                "status": "active",
                "backend": "pyaudio" if hasattr(self, '_pyaudio') and self._pyaudio else "mock",
                "config": {
                    "sample_rate": self.config.sample_rate,
                    "channels": self.config.channels,
                    "format": self.config.format.value,
                    "volume": self.config.volume
                },
                "devices": {
                    "input": {
                        "count": len(self._input_devices),
                        "current": self._current_input_device.name if self._current_input_device else None,
                        "available": [d.name for d in self._input_devices]
                    },
                    "output": {
                        "count": len(self._output_devices),
                        "current": self._current_output_device.name if self._current_output_device else None,
                        "available": [d.name for d in self._output_devices]
                    }
                },
                "activity": {
                    "recording": self._recording_active,
                    "playback": self._playback_active
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def __del__(self):
        """Cleanup on service destruction"""
        try:
            if hasattr(self, '_pyaudio') and self._pyaudio is not None:
                self._pyaudio.terminate()
        except Exception:
            pass
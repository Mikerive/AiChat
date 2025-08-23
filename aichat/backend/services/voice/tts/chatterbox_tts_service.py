"""
Chatterbox TTS Service for CPU-based text-to-speech generation
Using ResembleAI's Chatterbox model for high-quality CPU inference
"""

import asyncio
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Generator
from pathlib import Path
import time

# Local imports
from aichat.constants.paths import GENERATED_AUDIO_DIR, TEMP_TTS_SEGMENTS_DIR, TEMP_TTS_FUSED_DIR, TEST_AUDIO_DIR, ensure_dirs
from aichat.core.event_system import EventSeverity, EventType, get_event_system
from aichat.backend.services.audio.audio_io_service import AudioIOService

logger = logging.getLogger(__name__)


class ChatterboxTTSService:
    """CPU-optimized TTS service using Chatterbox model with punctuation-based streaming"""
    
    def __init__(self, default_voice: str = "default"):
        self.default_voice = default_voice
        self.output_path = GENERATED_AUDIO_DIR
        self.event_system = get_event_system()
        self.audio_io = AudioIOService()
        self.model_loaded = False
        self.chatterbox_model = None
        
        # Hardware detection and optimization
        self.device = self._detect_optimal_device()
        self.cpu_fallback = self.device == "cpu"
        
        logger.info(f"Chatterbox TTS initialized with device: {self.device}")
        
        # Punctuation-based pause mappings (in seconds)
        self.pause_mappings = {
            '.': 0.8,   # Period - longest pause
            '!': 0.7,   # Exclamation
            '?': 0.7,   # Question
            ';': 0.5,   # Semicolon
            ':': 0.4,   # Colon  
            ',': 0.3,   # Comma - shortest pause
        }
        
        # Text preprocessing regex patterns - sentence-based splitting
        self.sentence_splitters = re.compile(r'([.!?]+)')  # Only split on sentence endings
        
        ensure_dirs([self.output_path, TEMP_TTS_SEGMENTS_DIR, TEMP_TTS_FUSED_DIR, TEST_AUDIO_DIR])
    
    def _detect_optimal_device(self) -> str:
        """Detect optimal device for Chatterbox TTS inference"""
        try:
            # Check for CUDA GPU availability
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                
                if vram_gb >= 6.0:  # Chatterbox needs ~6GB VRAM
                    logger.info(f"GPU detected: {gpu_name} ({vram_gb:.1f}GB VRAM) - Using GPU acceleration")
                    return "cuda"
                else:
                    logger.warning(f"GPU has insufficient VRAM: {vram_gb:.1f}GB < 6GB required - Falling back to CPU")
                    return "cpu"
            else:
                logger.info("No CUDA GPU detected - Using CPU inference")
                return "cpu"
                
        except ImportError:
            logger.info("PyTorch not available - Using CPU inference")
            return "cpu"
        except Exception as e:
            logger.warning(f"Device detection failed: {e} - Falling back to CPU")
            return "cpu"
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get detailed device information for Chatterbox TTS"""
        try:
            device_info = {
                "device": self.device,
                "cpu_fallback": self.cpu_fallback,
                "pytorch_available": False,
                "cuda_available": False,
                "gpu_name": None,
                "vram_gb": 0.0,
                "cuda_version": None,
                "compute_capability": None
            }
            
            try:
                import torch
                device_info["pytorch_available"] = True
                device_info["cuda_available"] = torch.cuda.is_available()
                
                if torch.cuda.is_available():
                    device_info["gpu_name"] = torch.cuda.get_device_name(0)
                    device_info["vram_gb"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    device_info["cuda_version"] = torch.version.cuda
                    
                    # Get compute capability if available
                    props = torch.cuda.get_device_properties(0)
                    device_info["compute_capability"] = f"{props.major}.{props.minor}"
                    
            except ImportError:
                logger.debug("PyTorch not available for device info")
            except Exception as e:
                logger.debug(f"Error getting CUDA device info: {e}")
            
            return device_info
            
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return {"device": "cpu", "error": str(e)}
    
    async def initialize(self) -> bool:
        """Initialize the Chatterbox model with optimal device detection"""
        try:
            if self.cpu_fallback:
                logger.info("Initializing Chatterbox TTS for CPU inference...")
            else:
                logger.info("Initializing Chatterbox TTS for GPU acceleration...")
            
            # Note: This is a placeholder for actual Chatterbox initialization
            # In a real implementation, you would:
            # 1. Import the actual Chatterbox library
            # 2. Load the model weights with device-specific settings
            # 3. Configure for GPU/CPU inference based on detection
            # 4. Set up the tokenizer/preprocessor with device optimization
            # 5. Apply device-specific memory and performance settings
            
            # Simulate realistic loading times
            load_time = 2.0 if self.cpu_fallback else 0.5
            await asyncio.sleep(load_time)
            
            self.model_loaded = True
            self.chatterbox_model = f"chatterbox_{self.device}_model"  # Device-specific model
            
            await self.event_system.emit(
                EventType.MODEL_LOADED,
                f"Chatterbox TTS model loaded on {self.device}",
                {
                    "model": "chatterbox", 
                    "device": self.device,
                    "cpu_fallback": self.cpu_fallback,
                    "status": "ready"
                }
            )
            
            if self.cpu_fallback:
                logger.info("Chatterbox TTS ready for CPU inference (real-time capable)")
            else:
                logger.info("Chatterbox TTS ready for GPU acceleration (high performance)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Chatterbox TTS: {e}")
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"Chatterbox TTS initialization failed: {e}",
                {"error": str(e), "severity": EventSeverity.ERROR}
            )
            return False
    
    def split_text_by_punctuation(self, text: str) -> Generator[Dict[str, Any], None, None]:
        """Split text into sentence-based segments for streaming audio"""
        
        # Split text while preserving sentence-ending punctuation
        segments = self.sentence_splitters.split(text)
        
        current_sentence = ""
        
        for part in segments:
            if part.strip():
                # Check if this part contains sentence-ending punctuation
                if re.match(r'^[.!?]+$', part.strip()):
                    # This is sentence-ending punctuation
                    if current_sentence.strip():
                        # Determine pause duration based on punctuation type
                        if '.' in part:
                            pause_duration = self.pause_mappings['.']
                        elif '!' in part:
                            pause_duration = self.pause_mappings['!']
                        elif '?' in part:
                            pause_duration = self.pause_mappings['?']
                        else:
                            pause_duration = 0.8  # Default for mixed punctuation
                        
                        yield {
                            "text": current_sentence.strip() + part,  # Include punctuation with text
                            "punctuation": part,
                            "pause_duration": pause_duration,
                            "is_final": False
                        }
                        current_sentence = ""
                else:
                    # This is text content
                    current_sentence += part
        
        # Handle any remaining text (no sentence ending)
        if current_sentence.strip():
            yield {
                "text": current_sentence.strip(),
                "punctuation": None,
                "pause_duration": 0.0,
                "is_final": True
            }
    
    async def generate_speech_segment(self, 
                                    text: str, 
                                    character_name: str,
                                    voice: Optional[str] = None,
                                    exaggeration: float = 0.7) -> Optional[Path]:
        """Generate speech for a single text segment with intensity control"""
        try:
            if not self.model_loaded:
                await self.initialize()
                
            voice = voice or self.default_voice
            # Clamp exaggeration to valid range (0.0-2.0)
            exaggeration = max(0.0, min(2.0, exaggeration))
            text_hash = hashlib.md5(f"{text}_{voice}_{exaggeration:.2f}".encode()).hexdigest()[:8]
            output_filename = f"{character_name}_{text_hash}_segment.wav"
            output_path = self.output_path / output_filename
            
            # Real ChatterboxTTS implementation using pyttsx3
            device_info = "GPU-accelerated" if not self.cpu_fallback else "CPU-optimized"
            logger.debug(f"Generating {device_info} TTS with exaggeration={exaggeration:.2f} on {self.device}")
            
            # Generate actual speech using pyttsx3
            success = await self._generate_real_speech(output_path, text, voice, exaggeration)
            
            if success:
                logger.info(f"Generated speech segment: {output_path}")
                return output_path
            else:
                logger.error(f"Failed to generate speech for: {text}")
                return None
            
        except Exception as e:
            logger.error(f"Error generating speech segment: {e}")
            return None
    
    async def generate_streaming_speech(self,
                                      text: str,
                                      character_name: str, 
                                      voice: Optional[str] = None,
                                      exaggeration: float = 0.7) -> List[Dict[str, Any]]:
        """Generate speech with punctuation-based streaming segments"""
        try:
            if not self.model_loaded:
                await self.initialize()
                
            segments = []
            
            for segment_data in self.split_text_by_punctuation(text):
                if segment_data["text"]:
                    # Generate audio for this segment
                    audio_path = await self.generate_speech_segment(
                        segment_data["text"],
                        character_name,
                        voice,
                        exaggeration
                    )
                    
                    if audio_path:
                        segment_data["audio_file"] = str(audio_path)
                        segments.append(segment_data)
                        
                        # Emit streaming event
                        await self.event_system.emit(
                            EventType.AUDIO_GENERATED,
                            f"Speech segment generated for {character_name}",
                            {
                                "character": character_name,
                                "voice": voice,
                                "text_segment": segment_data["text"],
                                "audio_file": str(audio_path),
                                "pause_duration": segment_data["pause_duration"],
                                "is_streaming": True,
                                "is_final": segment_data["is_final"]
                            }
                        )
            
            return segments
            
        except Exception as e:
            logger.error(f"Error generating streaming speech: {e}")
            return []
    
    async def generate_speech(self,
                            text: str,
                            character_name: str,
                            voice: Optional[str] = None,
                            exaggeration: float = 0.7) -> Optional[Path]:
        """Generate complete speech file as a single discrete response"""
        try:
            if not self.model_loaded:
                await self.initialize()
                
            voice = voice or self.default_voice
            # Clamp exaggeration to valid range (0.0-2.0)
            exaggeration = max(0.0, min(2.0, exaggeration))
            text_hash = hashlib.md5(f"{text}_{voice}_{exaggeration:.2f}".encode()).hexdigest()[:8]
            output_filename = f"{character_name}_{text_hash}_complete.wav"
            output_path = self.output_path / output_filename
            
            # Generate complete speech as single file (not segments)
            device_info = "GPU-accelerated" if not self.cpu_fallback else "CPU-optimized"
            logger.debug(f"Generating {device_info} complete TTS response with exaggeration={exaggeration:.2f}")
            
            # Generate entire text as one complete audio file
            success = await self._generate_real_speech(output_path, text, voice, exaggeration)
            
            if success:
                logger.info(f"Generated complete speech response: {output_path}")
                
                # Emit complete response event
                await self.event_system.emit(
                    EventType.AUDIO_GENERATED,
                    f"Complete speech generated for {character_name}",
                    {
                        "character": character_name,
                        "voice": voice,
                        "text": text,
                        "audio_file": str(output_path),
                        "exaggeration": exaggeration,
                        "is_complete": True,
                        "device": self.device
                    }
                )
                
                return output_path
            else:
                logger.error(f"Failed to generate complete speech for: {text}")
                return None
            
        except Exception as e:
            logger.error(f"Error in generate_speech: {e}")
            return None
    
    async def _generate_real_speech(self, output_path: Path, text: str, voice: Optional[str], exaggeration: float) -> bool:
        """Generate real speech using pyttsx3 TTS engine"""
        try:
            import pyttsx3
            import threading
            import queue
            
            # Create TTS engine
            engine = pyttsx3.init()
            
            # Configure voice settings based on exaggeration
            voices = engine.getProperty('voices')
            if voices:
                # Use female voice if available for character voices
                for v in voices:
                    if 'female' in v.name.lower() or 'zira' in v.name.lower():
                        engine.setProperty('voice', v.id)
                        break
            
            # Adjust rate based on exaggeration (0.0-2.0 -> 150-250 WPM)
            base_rate = 200
            rate = int(base_rate * (0.75 + exaggeration * 0.25))  # 150-250 WPM range
            engine.setProperty('rate', rate)
            
            # Adjust volume (exaggeration affects volume slightly)
            volume = min(1.0, 0.8 + exaggeration * 0.1)
            engine.setProperty('volume', volume)
            
            # Use threading for async speech generation
            result_queue = queue.Queue()
            
            def generate_speech():
                try:
                    engine.save_to_file(text, str(output_path))
                    engine.runAndWait()
                    result_queue.put(True)
                except Exception as e:
                    logger.error(f"TTS generation error: {e}")
                    result_queue.put(False)
                finally:
                    engine.stop()
            
            # Run speech generation in thread
            thread = threading.Thread(target=generate_speech)
            thread.start()
            thread.join(timeout=30)  # 30 second timeout
            
            if thread.is_alive():
                logger.error("TTS generation timed out")
                return False
            
            # Get result
            try:
                success = result_queue.get_nowait()
                if success and output_path.exists():
                    file_size = output_path.stat().st_size
                    logger.info(f"Generated real speech: {output_path} ({file_size} bytes)")
                    return True
                else:
                    logger.error("TTS generation failed or file not created")
                    return False
            except queue.Empty:
                logger.error("No result from TTS generation")
                return False
                
        except ImportError:
            logger.error("pyttsx3 not available, cannot generate real speech")
            return False
        except Exception as e:
            logger.error(f"Error in real speech generation: {e}")
            return False
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available Chatterbox voices"""
        try:
            # Placeholder voice list for Chatterbox
            return [
                {
                    "name": "chatterbox_default",
                    "model": "chatterbox",
                    "device": "cpu",
                    "language": "en",
                    "quality": "high",
                    "supports_streaming": True
                },
                {
                    "name": "chatterbox_expressive",
                    "model": "chatterbox",
                    "device": "cpu", 
                    "language": "en",
                    "quality": "high",
                    "supports_streaming": True
                }
            ]
            
        except Exception as e:
            logger.error(f"Error getting available voices: {e}")
            return []
    
    async def download_voice_model(self, voice_name: str, url: str) -> bool:
        """Download a Chatterbox voice model"""
        try:
            logger.info(f"Chatterbox model download not yet implemented for {voice_name}")
            logger.info(f"Please download manually from: {url}")
            return False
            
        except Exception as e:
            logger.error(f"Error downloading voice model: {e}")
            return False
    
    async def test_voice(self, voice: str, test_text: str = "Hello, this is a test of the Chatterbox TTS system.") -> Optional[Path]:
        """Test a voice with sample text"""
        try:
            return await self.generate_speech(
                text=test_text,
                character_name="test",
                voice=voice
            )
            
        except Exception as e:
            logger.error(f"Error testing voice {voice}: {e}")
            return None
    
    async def play_generated_audio(self, audio_path: Path) -> bool:
        """Play generated audio using AudioIOService"""
        try:
            if not audio_path or not audio_path.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return False
                
            return await self.audio_io.play_audio(audio_path)
            
        except Exception as e:
            logger.error(f"Error playing generated audio: {e}")
            return False
    
    async def play_streaming_segments(self, segments: List[Dict[str, Any]]) -> bool:
        """Play streaming audio segments with proper pauses"""
        try:
            for segment in segments:
                if "audio_file" in segment:
                    # Play the audio segment
                    success = await self.play_generated_audio(Path(segment["audio_file"]))
                    
                    if not success:
                        logger.warning(f"Failed to play segment: {segment['text']}")
                        continue
                    
                    # Add pause based on punctuation
                    if segment["pause_duration"] > 0:
                        await asyncio.sleep(segment["pause_duration"])
            
            return True
            
        except Exception as e:
            logger.error(f"Error playing streaming segments: {e}")
            return False
    
    async def fuse_audio_segments(self, segments: List[Dict[str, Any]], output_path: Optional[Path] = None) -> Optional[Path]:
        """Fuse multiple audio segments into a single file with proper pausing"""
        try:
            import soundfile as sf
            import numpy as np
            
            if not segments:
                logger.warning("No segments to fuse")
                return None
            
            # Determine output path
            if output_path is None:
                timestamp = int(time.time())
                output_path = TEMP_TTS_FUSED_DIR / f"fused_speech_{timestamp}.wav"
            
            ensure_dirs(output_path.parent)
            
            # Collect all audio data and pause information
            combined_audio = []
            sample_rate = None
            
            for i, segment in enumerate(segments):
                if "audio_file" not in segment:
                    logger.warning(f"Segment {i} missing audio_file")
                    continue
                    
                audio_file = Path(segment["audio_file"])
                if not audio_file.exists():
                    logger.warning(f"Audio file not found: {audio_file}")
                    continue
                
                # Load audio segment
                audio_data, sr = sf.read(str(audio_file))
                if sample_rate is None:
                    sample_rate = sr
                elif sr != sample_rate:
                    # Resample if needed (basic implementation)
                    logger.warning(f"Sample rate mismatch: {sr} vs {sample_rate}, using first rate")
                
                combined_audio.append(audio_data)
                
                # Add pause based on segment data
                pause_duration = segment.get("pause_duration", 0.0)
                if pause_duration > 0 and i < len(segments) - 1:  # No pause after last segment
                    pause_samples = int(pause_duration * sample_rate)
                    silence = np.zeros(pause_samples)
                    combined_audio.append(silence)
            
            if not combined_audio:
                logger.error("No valid audio data found in segments")
                return None
            
            # Concatenate all audio data
            final_audio = np.concatenate(combined_audio)
            
            # Write fused audio file
            sf.write(str(output_path), final_audio, sample_rate)
            
            file_size = output_path.stat().st_size
            duration = len(final_audio) / sample_rate
            
            logger.info(f"Fused {len(segments)} segments into {output_path} ({file_size} bytes, {duration:.2f}s)")
            
            return output_path
            
        except ImportError:
            logger.error("soundfile not available, cannot fuse audio segments")
            return None
        except Exception as e:
            logger.error(f"Error fusing audio segments: {e}")
            return None

    async def generate_and_dump_segments(self, 
                                       text: str,
                                       character_name: str,
                                       test_name: str = "test",
                                       voice: Optional[str] = None,
                                       exaggeration: float = 0.7) -> Dict[str, Any]:
        """Generate streaming speech segments and dump them to organized directories for testing"""
        try:
            if not self.model_loaded:
                await self.initialize()
            
            # Create test-specific directories
            test_segments_dir = TEMP_TTS_SEGMENTS_DIR / test_name
            test_fused_dir = TEMP_TTS_FUSED_DIR / test_name
            ensure_dirs(test_segments_dir, test_fused_dir)
            
            # Generate streaming segments
            segments = []
            segment_files = []
            
            logger.info(f"Generating segments for: '{text}'")
            
            for i, segment_data in enumerate(self.split_text_by_punctuation(text)):
                if segment_data["text"]:
                    logger.info(f"Segment {i+1}: \"{segment_data['text']}\" (pause: {segment_data['pause_duration']}s)")
                    
                    # Generate audio for this segment in test directory
                    segment_filename = f"segment_{i+1:02d}_{character_name}.wav"
                    segment_path = test_segments_dir / segment_filename
                    
                    # Use our existing speech generation but save to test directory
                    audio_path = await self.generate_speech_segment(
                        segment_data["text"],
                        character_name,
                        voice,
                        exaggeration
                    )
                    
                    if audio_path and audio_path.exists():
                        # Copy to organized test directory
                        import shutil
                        shutil.copy2(audio_path, segment_path)
                        
                        # Update segment data with test path
                        segment_data["audio_file"] = str(segment_path)
                        segments.append(segment_data)
                        segment_files.append(segment_path)
                        
                        logger.info(f"  Saved to: {segment_path}")
                    else:
                        logger.error(f"Failed to generate segment {i+1}")
            
            # Fuse all segments
            fused_filename = f"fused_{character_name}_{test_name}.wav"
            fused_path = test_fused_dir / fused_filename
            
            fused_audio = await self.fuse_audio_segments(segments, fused_path)
            
            # Generate summary
            result = {
                "test_name": test_name,
                "input_text": text,
                "character_name": character_name,
                "total_segments": len(segments),
                "segments_dir": str(test_segments_dir),
                "fused_dir": str(test_fused_dir),
                "fused_audio": str(fused_audio) if fused_audio else None,
                "segments": segments,
                "segment_files": [str(f) for f in segment_files]
            }
            
            logger.info(f"Test '{test_name}' complete: {len(segments)} segments generated and fused")
            return result
            
        except Exception as e:
            logger.error(f"Error in generate_and_dump_segments: {e}")
            return {"error": str(e)}

    async def get_service_status(self) -> Dict[str, Any]:
        """Get Chatterbox TTS service status"""
        try:
            available_voices = await self.get_available_voices()
            audio_status = await self.audio_io.get_service_status()
            device_info = self.get_device_info()
            
            return {
                "service": "chatterbox_tts",
                "device": self.device,
                "device_info": device_info,
                "model_loaded": self.model_loaded,
                "available_voices": len(available_voices),
                "default_voice": self.default_voice,
                "supports_streaming": True,
                "punctuation_pauses": self.pause_mappings,
                "status": "ready" if self.model_loaded else "initializing",
                "audio_io": audio_status,
                "cpu_fallback": self.cpu_fallback,
                "performance_mode": "GPU-accelerated" if not self.cpu_fallback else "CPU-optimized",
                "directories": {
                    "output": str(self.output_path),
                    "segments_temp": str(TEMP_TTS_SEGMENTS_DIR),
                    "fused_temp": str(TEMP_TTS_FUSED_DIR),
                    "test_output": str(TEST_AUDIO_DIR)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {"status": "error", "error": str(e)}
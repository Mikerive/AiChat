"""
Streaming TTS Integration - Real-time text-to-speech with OpenRouter streaming
Converts streaming text from OpenRouter into real-time audio segments
"""

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable
from dataclasses import dataclass
from enum import Enum

# Local imports
from aichat.core.event_system import EventSeverity, EventType, get_event_system
from .smart_tts_selector import SmartTTSSelector, TTSBackend

logger = logging.getLogger(__name__)


class StreamingMode(Enum):
    """Streaming processing modes"""
    SENTENCE_BUFFER = "sentence_buffer"      # Wait for complete sentences
    PUNCTUATION_TRIGGER = "punctuation_trigger"  # Trigger on any punctuation
    WORD_COUNT_TRIGGER = "word_count_trigger"     # Trigger after N words
    TIME_BASED = "time_based"                     # Trigger after time delay


@dataclass
class StreamingConfig:
    """Configuration for streaming TTS processing"""
    mode: StreamingMode = StreamingMode.PUNCTUATION_TRIGGER
    buffer_size: int = 50  # Max characters to buffer
    word_trigger_count: int = 8  # Words before triggering (word mode)
    time_trigger_ms: int = 1500  # Time delay before triggering (time mode)
    min_segment_length: int = 3  # Minimum characters for TTS
    enable_realtime_playback: bool = True
    parallel_generation: bool = True  # Generate multiple segments in parallel
    lookahead_segments: int = 2  # Number of segments to generate ahead


class StreamingTTSIntegration:
    """Real-time TTS integration for streaming text from OpenRouter"""
    
    def __init__(self, 
                 tts_selector: SmartTTSSelector,
                 config: StreamingConfig = None):
        self.tts_selector = tts_selector
        self.config = config or StreamingConfig()
        self.event_system = get_event_system()
        
        # Streaming state
        self.text_buffer = ""
        self.pending_segments = []
        self.generated_segments = []
        self.is_streaming = False
        self.stream_start_time = 0.0
        
        # Performance tracking
        self.stream_stats = {
            "total_characters_processed": 0,
            "segments_generated": 0,
            "average_generation_time": 0.0,
            "average_playback_latency": 0.0,
            "buffer_overflows": 0,
            "successful_streams": 0
        }
        
        # Text processing patterns
        self.sentence_endings = re.compile(r'[.!?]+\s*')
        self.punctuation_triggers = re.compile(r'[.!?;:,—]+')
        self.word_pattern = re.compile(r'\b\w+\b')
    
    async def start_streaming_session(self, 
                                    character_name: str,
                                    voice: Optional[str] = None,
                                    speed: float = 1.0,
                                    pitch: float = 1.0,
                                    emotion_state: Optional[Dict[str, Any]] = None) -> str:
        """Start a new streaming TTS session"""
        try:
            session_id = f"stream_{int(time.time() * 1000)}"
            
            # Reset streaming state
            self.text_buffer = ""
            self.pending_segments = []
            self.generated_segments = []
            self.is_streaming = True
            self.stream_start_time = time.time()
            
            # Initialize TTS selector if needed
            if not self.tts_selector.active_service:
                await self.tts_selector.initialize()
            
            await self.event_system.emit(
                EventType.AUDIO_GENERATED,
                f"Started streaming TTS session for {character_name}",
                {
                    "session_id": session_id,
                    "character": character_name,
                    "voice": voice,
                    "streaming_mode": self.config.mode.value,
                    "tts_backend": self.tts_selector.optimal_backend
                }
            )
            
            logger.info(f"Started streaming TTS session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting streaming session: {e}")
            raise
    
    async def process_streaming_text(self,
                                   text_chunk: str,
                                   character_name: str,
                                   session_id: str,
                                   voice: Optional[str] = None,
                                   speed: float = 1.0,
                                   pitch: float = 1.0,
                                   emotion_state: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Process incoming streaming text and generate TTS segments"""
        try:
            if not self.is_streaming:
                logger.warning("Received text for inactive streaming session")
                return []
            
            # Add to buffer
            self.text_buffer += text_chunk
            self.stream_stats["total_characters_processed"] += len(text_chunk)
            
            # Determine if we should trigger TTS generation
            segments_to_generate = await self._check_trigger_conditions()
            
            generated_segments = []
            
            for segment_text in segments_to_generate:
                if len(segment_text.strip()) >= self.config.min_segment_length:
                    # Generate TTS for segment
                    segment_data = await self._generate_tts_segment(
                        segment_text.strip(),
                        character_name,
                        voice,
                        speed,
                        pitch,
                        emotion_state,
                        session_id
                    )
                    
                    if segment_data:
                        generated_segments.append(segment_data)
                        self.generated_segments.append(segment_data)
                        
                        # Emit streaming event
                        await self.event_system.emit(
                            EventType.AUDIO_GENERATED,
                            f"Streaming TTS segment generated",
                            {
                                "session_id": session_id,
                                "character": character_name,
                                "text_segment": segment_text.strip(),
                                "audio_file": segment_data.get("audio_file"),
                                "is_streaming": True,
                                "generation_time": segment_data.get("generation_time", 0)
                            }
                        )
                        
                        # Auto-play if enabled
                        if self.config.enable_realtime_playback:
                            asyncio.create_task(self._play_segment_when_ready(segment_data))
            
            return generated_segments
            
        except Exception as e:
            logger.error(f"Error processing streaming text: {e}")
            return []
    
    async def _check_trigger_conditions(self) -> List[str]:
        """Check if conditions are met to trigger TTS generation"""
        segments_to_generate = []
        
        try:
            if self.config.mode == StreamingMode.SENTENCE_BUFFER:
                # Wait for complete sentences
                sentences = self.sentence_endings.split(self.text_buffer)
                if len(sentences) > 1:
                    # Process all complete sentences
                    for sentence in sentences[:-1]:
                        if sentence.strip():
                            segments_to_generate.append(sentence.strip())
                    # Keep the last incomplete sentence in buffer
                    self.text_buffer = sentences[-1]
                    
            elif self.config.mode == StreamingMode.PUNCTUATION_TRIGGER:
                # Trigger on any major punctuation
                parts = self.punctuation_triggers.split(self.text_buffer)
                if len(parts) > 1:
                    # Process all parts except the last incomplete one
                    for i in range(len(parts) - 1):
                        if parts[i].strip():
                            segments_to_generate.append(parts[i].strip())
                    # Keep the last part in buffer
                    self.text_buffer = parts[-1]
                    
            elif self.config.mode == StreamingMode.WORD_COUNT_TRIGGER:
                # Trigger after N words
                words = self.word_pattern.findall(self.text_buffer)
                if len(words) >= self.config.word_trigger_count:
                    # Take words up to the trigger count
                    trigger_text = ' '.join(words[:self.config.word_trigger_count])
                    segments_to_generate.append(trigger_text)
                    # Remove processed words from buffer
                    remaining_text = ' '.join(words[self.config.word_trigger_count:])
                    self.text_buffer = remaining_text
                    
            elif self.config.mode == StreamingMode.TIME_BASED:
                # Trigger after time delay (if buffer has content)
                if (self.text_buffer.strip() and 
                    time.time() - self.stream_start_time > self.config.time_trigger_ms / 1000.0):
                    segments_to_generate.append(self.text_buffer.strip())
                    self.text_buffer = ""
                    self.stream_start_time = time.time()
            
            # Check buffer overflow
            if len(self.text_buffer) > self.config.buffer_size:
                logger.warning(f"Text buffer overflow ({len(self.text_buffer)} chars)")
                self.stream_stats["buffer_overflows"] += 1
                # Force generation of current buffer content
                if self.text_buffer.strip():
                    segments_to_generate.append(self.text_buffer.strip())
                self.text_buffer = ""
                
        except Exception as e:
            logger.error(f"Error checking trigger conditions: {e}")
            
        return segments_to_generate
    
    async def _generate_tts_segment(self,
                                  text: str,
                                  character_name: str,
                                  voice: Optional[str],
                                  speed: float,
                                  pitch: float,
                                  emotion_state: Optional[Dict[str, Any]],
                                  session_id: str) -> Optional[Dict[str, Any]]:
        """Generate TTS for a single text segment"""
        try:
            start_time = time.time()
            
            # Use streaming TTS if available (Orpheus real-time)
            if hasattr(self.tts_selector.active_service, 'generate_realtime_stream'):
                # Real-time streaming generation
                audio_segments = []
                async for segment in self.tts_selector.active_service.generate_realtime_stream(
                    text, character_name, voice, speed, pitch, emotion_state
                ):
                    audio_segments.append(segment)
                
                if audio_segments:
                    generation_time = time.time() - start_time
                    
                    # Combine segments or use first one
                    primary_segment = audio_segments[0]
                    primary_segment.update({
                        "session_id": session_id,
                        "generation_time": generation_time,
                        "is_realtime_stream": True,
                        "total_segments": len(audio_segments)
                    })
                    
                    return primary_segment
                    
            else:
                # Standard streaming generation
                segments = await self.tts_selector.generate_streaming_speech(
                    text, character_name, voice, speed, pitch, emotion_state
                )
                
                if segments:
                    generation_time = time.time() - start_time
                    
                    primary_segment = segments[0]
                    primary_segment.update({
                        "session_id": session_id,
                        "generation_time": generation_time,
                        "is_realtime_stream": False,
                        "total_segments": len(segments)
                    })
                    
                    # Update performance stats
                    self.stream_stats["segments_generated"] += 1
                    self.stream_stats["average_generation_time"] = (
                        (self.stream_stats["average_generation_time"] * 
                         (self.stream_stats["segments_generated"] - 1) + generation_time) / 
                        self.stream_stats["segments_generated"]
                    )
                    
                    return primary_segment
                    
            return None
            
        except Exception as e:
            logger.error(f"Error generating TTS segment: {e}")
            return None
    
    async def _play_segment_when_ready(self, segment_data: Dict[str, Any]):
        """Play audio segment as soon as it's ready"""
        try:
            if "audio_file" in segment_data:
                from pathlib import Path
                audio_path = Path(segment_data["audio_file"])
                
                # Play immediately
                success = await self.tts_selector.play_generated_audio(audio_path)
                
                if success:
                    # Add any pause duration
                    pause_duration = segment_data.get("pause_duration", 0.0)
                    if pause_duration > 0:
                        await asyncio.sleep(pause_duration)
                else:
                    logger.warning(f"Failed to play streaming segment: {segment_data['text']}")
                    
        except Exception as e:
            logger.error(f"Error playing streaming segment: {e}")
    
    async def finalize_streaming_session(self,
                                       character_name: str,
                                       session_id: str,
                                       voice: Optional[str] = None,
                                       speed: float = 1.0,
                                       pitch: float = 1.0,
                                       emotion_state: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Finalize streaming session and process any remaining buffer content"""
        try:
            final_segments = []
            
            # Process any remaining text in buffer
            if self.text_buffer.strip():
                final_segment = await self._generate_tts_segment(
                    self.text_buffer.strip(),
                    character_name,
                    voice,
                    speed,
                    pitch,
                    emotion_state,
                    session_id
                )
                
                if final_segment:
                    final_segment["is_final"] = True
                    final_segments.append(final_segment)
                    
                    if self.config.enable_realtime_playback:
                        await self._play_segment_when_ready(final_segment)
            
            # Update stats
            stream_duration = time.time() - self.stream_start_time
            self.stream_stats["successful_streams"] += 1
            
            # Reset streaming state
            self.is_streaming = False
            self.text_buffer = ""
            
            await self.event_system.emit(
                EventType.AUDIO_GENERATED,
                f"Finalized streaming TTS session for {character_name}",
                {
                    "session_id": session_id,
                    "character": character_name,
                    "stream_duration": stream_duration,
                    "total_segments": len(self.generated_segments),
                    "final_segments": len(final_segments),
                    "stream_stats": self.stream_stats
                }
            )
            
            logger.info(f"Finalized streaming session {session_id} - {len(self.generated_segments)} segments")
            return final_segments
            
        except Exception as e:
            logger.error(f"Error finalizing streaming session: {e}")
            return []
    
    async def create_openrouter_streaming_handler(self,
                                                character_name: str,
                                                voice: Optional[str] = None,
                                                speed: float = 1.0,
                                                pitch: float = 1.0,
                                                emotion_state: Optional[Dict[str, Any]] = None) -> Callable:
        """Create a handler function for OpenRouter streaming responses"""
        
        session_id = await self.start_streaming_session(
            character_name, voice, speed, pitch, emotion_state
        )
        
        async def handle_openrouter_chunk(chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """Handle individual chunks from OpenRouter streaming"""
            try:
                # Extract text content from OpenRouter chunk
                content = ""
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                
                if content:
                    # Process the streaming text
                    segments = await self.process_streaming_text(
                        content, character_name, session_id, voice, speed, pitch, emotion_state
                    )
                    
                    return {
                        "text_chunk": content,
                        "tts_segments": segments,
                        "session_id": session_id
                    }
                
                return None
                
            except Exception as e:
                logger.error(f"Error handling OpenRouter chunk: {e}")
                return None
        
        async def finalize_handler() -> List[Dict[str, Any]]:
            """Finalize the streaming session"""
            return await self.finalize_streaming_session(
                character_name, session_id, voice, speed, pitch, emotion_state
            )
        
        # Return both the chunk handler and finalizer
        handle_openrouter_chunk.finalize = finalize_handler
        return handle_openrouter_chunk
    
    def get_streaming_stats(self) -> Dict[str, Any]:
        """Get comprehensive streaming performance statistics"""
        return {
            "config": {
                "mode": self.config.mode.value,
                "buffer_size": self.config.buffer_size,
                "realtime_playback": self.config.enable_realtime_playback,
                "parallel_generation": self.config.parallel_generation
            },
            "current_state": {
                "is_streaming": self.is_streaming,
                "buffer_length": len(self.text_buffer),
                "pending_segments": len(self.pending_segments),
                "generated_segments": len(self.generated_segments)
            },
            "performance": self.stream_stats,
            "tts_backend": self.tts_selector.optimal_backend if self.tts_selector else "unknown"
        }
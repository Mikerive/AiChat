"""
Simple LLM Service with Two-Stage Emotion Processing
Replaces complex JSON structures with clean single-word emotion queries
"""

import logging
import asyncio
from typing import Dict, Optional, Tuple, Any, List, AsyncGenerator
from dataclasses import dataclass

# Local imports
try:
    from .simple_emotion_detector import SimpleEmotionDetector, EmotionalResponseGenerator
    from .compact_voice_controller import CompactVoiceController
    from .sbert_emotion_detector import SBERTEmotionDetector
    from ..emotion_parser import IntensityParser
except ImportError:
    # Fallback for direct module testing
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    
    from simple_emotion_detector import SimpleEmotionDetector, EmotionalResponseGenerator
    from compact_voice_controller import CompactVoiceController
    from sbert_emotion_detector import SBERTEmotionDetector
    
    # Add parent path for emotion_parser
    sys.path.append(str(Path(__file__).parent.parent))
    from emotion_parser import IntensityParser

logger = logging.getLogger(__name__)


@dataclass
class SimpleEmotionalResponse:
    """Clean response structure without complex JSON"""
    text: str
    detected_emotion: str
    voice_speed: float
    voice_pitch: float
    confidence: float = 1.0


@dataclass
class CharacterProfile:
    """Simplified character profile"""
    name: str
    personality: str
    profile: str
    default_voice: str = "default"


class SimpleLLMService:
    """
    Simplified LLM service using the efficient two-stage approach:
    1. Query emotion with single word response
    2. Generate response using detected emotion
    
    No complex JSON, no structured output leakage, just clean emotion detection
    """
    
    def __init__(self, openai_key: Optional[str] = None, anthropic_key: Optional[str] = None):
        # Initialize core components
        self.emotion_detector = SimpleEmotionDetector(openai_key)
        self.response_generator = EmotionalResponseGenerator(openai_key)
        self.voice_controller = CompactVoiceController()
        self.intensity_parser = IntensityParser()
        
        # Performance tracking
        self.stats = {
            "total_interactions": 0,
            "average_emotion_detection_time": 0.0,
            "average_response_generation_time": 0.0,
            "emotion_distribution": {},
            "voice_parameter_usage": {},
            "errors": 0
        }
        
        logger.info("Simple LLM Service initialized with emotion-first streaming processing")
    
    async def process_message(
        self,
        user_message: str,
        character: CharacterProfile,
        conversation_context: str = "",
        use_voice_modulation: bool = True
    ) -> SimpleEmotionalResponse:
        """
        Process user message with two-stage emotion approach
        
        Stage 1: Detect emotion with single word
        Stage 2: Generate response using detected emotion
        
        Args:
            user_message: User's input message
            character: Character profile for response generation
            conversation_context: Previous conversation context
            use_voice_modulation: Whether to apply voice parameter modulation
            
        Returns:
            SimpleEmotionalResponse with text, emotion, and voice parameters
        """
        try:
            import time
            total_start = time.time()
            
            # Stage 1: Detect emotion (single word, fast)
            emotion_start = time.time()
            detected_emotion = await self.emotion_detector.detect_emotion(
                user_message, conversation_context
            )
            emotion_time = time.time() - emotion_start
            
            # Stage 2: Generate voice parameters (mathematical, very fast)
            voice_speed, voice_pitch = 1.0, 1.0
            if use_voice_modulation:
                voice_speed, voice_pitch = self.voice_controller.get_voice_parameters(detected_emotion)
            
            # Stage 3: Generate emotional response (using detected emotion)
            response_start = time.time()
            response_text = await self.response_generator.generate_emotional_response(
                character_name=character.name,
                character_personality=character.personality,
                character_profile=character.profile,
                detected_emotion=detected_emotion,
                user_message=user_message,
                conversation_context=conversation_context
            )
            response_time = time.time() - response_start
            
            # Update statistics
            total_time = time.time() - total_start
            self._update_stats(detected_emotion, emotion_time, response_time, voice_speed, voice_pitch)
            
            logger.debug(
                f"Processed message in {total_time:.3f}s: "
                f"emotion='{detected_emotion}' (detection: {emotion_time:.3f}s, "
                f"response: {response_time:.3f}s)"
            )
            
            return SimpleEmotionalResponse(
                text=response_text,
                detected_emotion=detected_emotion,
                voice_speed=voice_speed,
                voice_pitch=voice_pitch,
                confidence=1.0
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.stats["errors"] += 1
            
            # Return safe fallback
            return SimpleEmotionalResponse(
                text="I understand. Let me help you with that.",
                detected_emotion="neutral",
                voice_speed=1.0,
                voice_pitch=1.0,
                confidence=0.0
            )
    
    async def get_emotion_only(self, user_message: str, context: str = "") -> str:
        """
        Get just the emotion detection (Stage 1 only)
        Useful for real-time emotion tracking without full response generation
        
        Args:
            user_message: User's input message
            context: Optional context
            
        Returns:
            Single emotion word
        """
        try:
            return await self.emotion_detector.detect_emotion(user_message, context)
        except Exception as e:
            logger.error(f"Error detecting emotion: {e}")
            return "neutral"
    
    async def generate_response_with_emotion(
        self,
        user_message: str,
        character: CharacterProfile,
        forced_emotion: str,
        conversation_context: str = ""
    ) -> SimpleEmotionalResponse:
        """
        Generate response with a forced emotion (skip Stage 1)
        Useful when emotion is already known or manually specified
        
        Args:
            user_message: User's input message
            character: Character profile
            forced_emotion: Emotion to use for response generation
            conversation_context: Previous conversation context
            
        Returns:
            SimpleEmotionalResponse using the forced emotion
        """
        try:
            # Skip emotion detection, use forced emotion
            voice_speed, voice_pitch = self.voice_controller.get_voice_parameters(forced_emotion)
            
            response_text = await self.response_generator.generate_emotional_response(
                character_name=character.name,
                character_personality=character.personality,
                character_profile=character.profile,
                detected_emotion=forced_emotion,
                user_message=user_message,
                conversation_context=conversation_context
            )
            
            return SimpleEmotionalResponse(
                text=response_text,
                detected_emotion=forced_emotion,
                voice_speed=voice_speed,
                voice_pitch=voice_pitch,
                confidence=1.0
            )
            
        except Exception as e:
            logger.error(f"Error generating response with forced emotion '{forced_emotion}': {e}")
            return SimpleEmotionalResponse(
                text="I understand what you're saying.",
                detected_emotion=forced_emotion,
                voice_speed=1.0,
                voice_pitch=1.0,
                confidence=0.0
            )
    
    async def batch_process_emotions(self, messages: List[str]) -> List[str]:
        """
        Process multiple messages for emotion detection only (efficient batch processing)
        
        Args:
            messages: List of user messages
            
        Returns:
            List of detected emotions
        """
        try:
            # Process emotions concurrently for efficiency
            tasks = [self.emotion_detector.detect_emotion(msg) for msg in messages]
            emotions = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions
            result = []
            for emotion in emotions:
                if isinstance(emotion, Exception):
                    logger.warning(f"Emotion detection failed: {emotion}")
                    result.append("neutral")
                else:
                    result.append(emotion)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in batch emotion processing: {e}")
            return ["neutral"] * len(messages)
    
    def get_voice_parameters_for_emotion(self, emotion: str) -> Tuple[float, float]:
        """
        Get voice parameters for a specific emotion (Stage 2 only)
        
        Args:
            emotion: Single emotion word
            
        Returns:
            Tuple of (speed, pitch)
        """
        return self.voice_controller.get_voice_parameters(emotion)
    
    def create_emotional_system_prompt(
        self,
        character: CharacterProfile,
        detected_emotion: str,
        context: str = ""
    ) -> str:
        """
        Create enhanced system prompt that embodies the detected emotion
        
        Args:
            character: Character profile
            detected_emotion: Emotion detected from user
            context: Additional context
            
        Returns:
            System prompt that makes character embody the emotion
        """
        try:
            # Get voice parameters for the emotion
            voice_speed, voice_pitch = self.voice_controller.get_voice_parameters(detected_emotion)
            
            # Create voice settings object
            from aichat.models.schemas import VoiceSettings, EmotionState
            
            voice_settings = VoiceSettings(speed=voice_speed, pitch=voice_pitch)
            emotion_state = EmotionState(
                emotion=detected_emotion,
                intensity=0.7,  # Default intensity
                context=f"User is feeling {detected_emotion}"
            )
            
            # Generate emotional prompt
            return self.system_prompt_generator.generate_emotional_prompt(
                character_name=character.name,
                character_personality=character.personality,
                character_profile=character.profile,
                emotion_state=emotion_state,
                voice_settings=voice_settings,
                conversation_context=context
            )
            
        except Exception as e:
            logger.error(f"Error creating emotional system prompt: {e}")
            return f"You are {character.name}. Respond naturally and helpfully."
    
    def get_similar_emotions(self, emotion: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Get emotions similar to the given emotion"""
        return self.voice_controller.find_similar_emotions(emotion, limit)
    
    def calibrate_voice_sensitivity(self, speed_sensitivity: float = 1.0, pitch_sensitivity: float = 1.0):
        """Calibrate voice parameter sensitivity"""
        self.voice_controller.calibrate_voice_mapping(speed_sensitivity, pitch_sensitivity)
        logger.info(f"Voice sensitivity calibrated: speed={speed_sensitivity}, pitch={pitch_sensitivity}")
    
    def _update_stats(self, emotion: str, emotion_time: float, response_time: float, speed: float, pitch: float):
        """Update performance statistics"""
        self.stats["total_interactions"] += 1
        total = self.stats["total_interactions"]
        
        # Update average times
        current_emotion_avg = self.stats["average_emotion_detection_time"]
        self.stats["average_emotion_detection_time"] = (
            (current_emotion_avg * (total - 1) + emotion_time) / total
        )
        
        current_response_avg = self.stats["average_response_generation_time"]
        self.stats["average_response_generation_time"] = (
            (current_response_avg * (total - 1) + response_time) / total
        )
        
        # Update emotion distribution
        if emotion not in self.stats["emotion_distribution"]:
            self.stats["emotion_distribution"][emotion] = 0
        self.stats["emotion_distribution"][emotion] += 1
        
        # Update voice parameter usage
        voice_key = f"speed_{speed:.2f}_pitch_{pitch:.2f}"
        if voice_key not in self.stats["voice_parameter_usage"]:
            self.stats["voice_parameter_usage"][voice_key] = 0
        self.stats["voice_parameter_usage"][voice_key] += 1
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            "service_stats": self.stats,
            "emotion_detector_stats": self.emotion_detector.get_performance_stats(),
            "voice_controller_stats": self.voice_controller.get_performance_stats(),
            "emotion_space_info": self.voice_controller.get_emotion_space_info(),
            "system_health": {
                "total_errors": self.stats["errors"],
                "error_rate": self.stats["errors"] / max(self.stats["total_interactions"], 1),
                "average_total_time": (
                    self.stats["average_emotion_detection_time"] + 
                    self.stats["average_response_generation_time"]
                ),
                "most_common_emotions": sorted(
                    self.stats["emotion_distribution"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5] if self.stats["emotion_distribution"] else []
            }
        }
    
    def clear_all_caches(self):
        """Clear all performance caches"""
        self.emotion_detector.clear_cache()
        self.voice_controller.clear_cache()
        logger.info("All LLM service caches cleared")

    async def process_streaming_with_intensity_first(
        self,
        user_message: str,
        character: CharacterProfile,
        conversation_context: str = ""
    ) -> AsyncGenerator[Tuple[Optional[float], str], None]:
        """
        Process message with intensity-first streaming approach
        
        LLM generates intensity marker first, then streams the response text.
        This allows Chatterbox TTS to apply consistent exaggeration to the entire response.
        
        Args:
            user_message: User's input message
            character: Character profile for response generation  
            conversation_context: Previous conversation context
            
        Yields:
            Tuples of (exaggeration, text_chunk) where exaggeration is set once in first chunk
        """
        try:
            # Create intensity-aware system prompt
            system_prompt = f"""You are {character.name}, a character with this personality: {character.personality}

Profile: {character.profile}

IMPORTANT: You must start your response with an intensity marker in this exact format: [INTENSITY: level]

Valid intensity levels:
- flat/monotone: Completely emotionless, robotic delivery
- low/subdued: Minimal expression, quiet tone
- minimal/calm: Very slight expression
- neutral/balanced: Natural baseline 
- normal/default: Standard conversational tone (recommended)
- moderate/medium: Slightly more expressive
- high/strong: Noticeably expressive and energetic
- dramatic/intense: Clearly dramatic delivery
- extreme/maximum: Highly theatrical
- theatrical: Maximum dramatic expression

Choose the intensity that best represents how {character.name} would speak when responding to this message. Then provide your natural response.

Example: [INTENSITY: high] I can't wait to help you with that amazing project!

Previous context: {conversation_context}
User message: {user_message}

Your response (start with intensity marker):"""

            # Stream response from LLM
            current_exaggeration = None
            first_chunk = True
            
            # Simulate LLM streaming (replace with actual LLM streaming call)
            # This would be replaced with actual OpenAI/Anthropic streaming
            mock_response = f"[INTENSITY: high] Hello! I'm {character.name} and I'm excited to help you with that. This is a streaming response that would come from the actual LLM."
            
            # Split into chunks to simulate streaming
            words = mock_response.split()
            current_chunk = ""
            
            for i, word in enumerate(words):
                current_chunk += word + " "
                
                # Send chunk every 3-5 words (simulate streaming)
                if i % 4 == 0 or i == len(words) - 1:
                    chunk_text = current_chunk.strip()
                    
                    if first_chunk:
                        # Extract intensity from first chunk
                        current_exaggeration = self.intensity_parser.extract_intensity_from_chunk(chunk_text)
                        clean_text = self.intensity_parser.strip_intensity_marker(chunk_text)
                        first_chunk = False
                        
                        if clean_text.strip():  # Only yield if there's actual content
                            yield (current_exaggeration, clean_text)
                    else:
                        # Subsequent chunks just have text, exaggeration is already set
                        if chunk_text.strip():
                            yield (None, chunk_text)
                    
                    current_chunk = ""
                    
                    # Simulate streaming delay
                    await asyncio.sleep(0.1)
            
            logger.info(f"Intensity-first streaming completed with exaggeration: {current_exaggeration}")
            
        except Exception as e:
            logger.error(f"Error in intensity-first streaming: {e}")
            yield (None, "I understand what you're saying.")

    def get_intensity_first_system_prompt(self, character: CharacterProfile) -> str:
        """
        Create system prompt for intensity-first LLM responses
        
        Args:
            character: Character profile
            
        Returns:
            System prompt that instructs LLM to output intensity first
        """
        return f"""You are {character.name}, a character with this personality: {character.personality}

Profile: {character.profile}

CRITICAL INSTRUCTION: You MUST start every response with an intensity marker in this exact format: [INTENSITY: level]

Valid intensity levels:
- flat/monotone: Completely emotionless, robotic delivery
- low/subdued: Minimal expression, quiet tone  
- minimal/calm: Very slight expression
- neutral/balanced: Natural baseline
- normal/default: Standard conversational tone (recommended)
- moderate/medium: Slightly more expressive
- high/strong: Noticeably expressive and energetic
- dramatic/intense: Clearly dramatic delivery
- extreme/maximum: Highly theatrical
- theatrical: Maximum dramatic expression

Choose the intensity that best represents how {character.name} would speak when responding. Then provide your natural response.

Example format:
[INTENSITY: high] I can't wait to help you with that amazing project!

This intensity will control voice exaggeration (0.0-2.0) in Chatterbox TTS, so choose accurately based on {character.name}'s personality and the context of the conversation."""
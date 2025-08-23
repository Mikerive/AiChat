"""
Simple Single-Word Emotion Detection with PydanticAI
Efficient two-stage emotion processing: query emotion, then respond
"""

import logging
import asyncio
from typing import Dict, Optional, Tuple, Any
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

logger = logging.getLogger(__name__)


class EmotionResponse(BaseModel):
    """Simple single-word emotion response"""
    emotion: str


class VoiceParameters(BaseModel):
    """Compact voice parameter mapping"""
    speed: float
    pitch: float


class SimpleEmotionDetector:
    """
    Simple, efficient emotion detection using single-word responses.
    Two-stage process: emotion query -> response generation
    """
    
    def __init__(self, openai_key: Optional[str] = None):
        self.openai_key = openai_key
        
        # Import centralized config
        from ..model_config import model_config
        
        # Use centralized model selection for consistency
        default_spec = model_config.get_default_model()
        model_name = default_spec.name if default_spec and default_spec.cost_per_1m_tokens <= 0.5 else "gpt-4o-mini"
        
        # Create lightweight emotion detection agent
        openai_model = OpenAIModel(model_name)
        if openai_key:
            import os
            os.environ["OPENAI_API_KEY"] = openai_key
        
        self.emotion_agent = Agent(
            model=openai_model,
            system_prompt="""You are an emotion detector. Analyze the user's message and respond with exactly ONE word that best describes their emotional state.

Choose from these emotions based on what you detect:
- happy, excited, joyful, enthusiastic, elated
- sad, disappointed, melancholy, dejected, gloomy  
- angry, frustrated, irritated, furious, annoyed
- worried, anxious, nervous, concerned, stressed
- curious, interested, intrigued, fascinated, wondering
- calm, peaceful, relaxed, content, serene
- confused, puzzled, uncertain, bewildered, perplexed
- surprised, amazed, astonished, startled, shocked
- neutral, indifferent, apathetic, detached, bland

Respond with ONLY the single word that best matches their emotion. No explanations, no punctuation, just the emotion word."""
        )
        
        # Emotion-to-voice parameter mapping (compact N-dimensional space)
        self.emotion_voice_map = {
            # Positive emotions - higher energy
            "happy": {"speed": 1.1, "pitch": 1.05},
            "excited": {"speed": 1.2, "pitch": 1.1}, 
            "joyful": {"speed": 1.1, "pitch": 1.08},
            "enthusiastic": {"speed": 1.15, "pitch": 1.06},
            "elated": {"speed": 1.2, "pitch": 1.12},
            
            # Negative emotions - lower energy
            "sad": {"speed": 0.85, "pitch": 0.92},
            "disappointed": {"speed": 0.9, "pitch": 0.95},
            "melancholy": {"speed": 0.8, "pitch": 0.88},
            "dejected": {"speed": 0.75, "pitch": 0.85},
            "gloomy": {"speed": 0.8, "pitch": 0.9},
            
            # Anger - intense but controlled
            "angry": {"speed": 1.05, "pitch": 0.95},
            "frustrated": {"speed": 1.0, "pitch": 0.98},
            "irritated": {"speed": 1.02, "pitch": 0.96},
            "furious": {"speed": 1.1, "pitch": 0.92},
            "annoyed": {"speed": 1.0, "pitch": 0.97},
            
            # Anxiety - faster but uncertain
            "worried": {"speed": 1.05, "pitch": 1.02},
            "anxious": {"speed": 1.1, "pitch": 1.05},
            "nervous": {"speed": 1.08, "pitch": 1.03},
            "concerned": {"speed": 1.0, "pitch": 1.01},
            "stressed": {"speed": 1.12, "pitch": 1.04},
            
            # Curiosity - engaged and alert
            "curious": {"speed": 1.05, "pitch": 1.03},
            "interested": {"speed": 1.02, "pitch": 1.02},
            "intrigued": {"speed": 1.0, "pitch": 1.01},
            "fascinated": {"speed": 1.08, "pitch": 1.05},
            "wondering": {"speed": 0.98, "pitch": 1.01},
            
            # Calm states - steady and controlled
            "calm": {"speed": 0.95, "pitch": 1.0},
            "peaceful": {"speed": 0.9, "pitch": 0.98},
            "relaxed": {"speed": 0.92, "pitch": 0.99},
            "content": {"speed": 0.98, "pitch": 1.0},
            "serene": {"speed": 0.88, "pitch": 0.97},
            
            # Confusion - hesitant
            "confused": {"speed": 0.92, "pitch": 1.02},
            "puzzled": {"speed": 0.95, "pitch": 1.01},
            "uncertain": {"speed": 0.9, "pitch": 1.0},
            "bewildered": {"speed": 0.88, "pitch": 1.03},
            "perplexed": {"speed": 0.93, "pitch": 1.01},
            
            # Surprise - quick and high
            "surprised": {"speed": 1.15, "pitch": 1.08},
            "amazed": {"speed": 1.1, "pitch": 1.06},
            "astonished": {"speed": 1.12, "pitch": 1.1},
            "startled": {"speed": 1.2, "pitch": 1.12},
            "shocked": {"speed": 1.05, "pitch": 1.04},
            
            # Neutral - baseline
            "neutral": {"speed": 1.0, "pitch": 1.0},
            "indifferent": {"speed": 0.98, "pitch": 1.0},
            "apathetic": {"speed": 0.95, "pitch": 0.98},
            "detached": {"speed": 0.96, "pitch": 0.99},
            "bland": {"speed": 0.97, "pitch": 1.0},
        }
        
        # Performance tracking
        self.detection_stats = {
            "total_detections": 0,
            "average_response_time": 0.0,
            "emotion_frequency": {},
            "voice_parameter_cache": {}
        }
    
    async def detect_emotion(self, user_message: str, context: str = "") -> str:
        """
        Detect emotion from user message with single word response
        
        Args:
            user_message: The user's input message
            context: Optional conversation context
            
        Returns:
            Single emotion word
        """
        try:
            import time
            start_time = time.time()
            
            # Prepare input with context if provided
            input_text = user_message
            if context:
                input_text = f"Context: {context}\nUser message: {user_message}"
            
            # Get emotion from lightweight agent
            result = await self.emotion_agent.run(input_text)
            emotion = str(result.data).lower().strip()
            
            # Update performance stats
            detection_time = time.time() - start_time
            self._update_stats(emotion, detection_time)
            
            logger.debug(f"Detected emotion '{emotion}' in {detection_time:.3f}s")
            return emotion
            
        except Exception as e:
            logger.error(f"Error detecting emotion: {e}")
            return "neutral"  # Safe fallback
    
    def get_voice_parameters(self, emotion: str) -> VoiceParameters:
        """
        Get voice parameters for detected emotion
        
        Args:
            emotion: Single emotion word
            
        Returns:
            VoiceParameters with speed and pitch adjustments
        """
        try:
            # Check cache first
            if emotion in self.detection_stats["voice_parameter_cache"]:
                cached = self.detection_stats["voice_parameter_cache"][emotion]
                return VoiceParameters(speed=cached["speed"], pitch=cached["pitch"])
            
            # Get parameters from emotion map
            params = self.emotion_voice_map.get(emotion, {"speed": 1.0, "pitch": 1.0})
            
            # Cache for performance
            self.detection_stats["voice_parameter_cache"][emotion] = params
            
            return VoiceParameters(speed=params["speed"], pitch=params["pitch"])
            
        except Exception as e:
            logger.error(f"Error getting voice parameters for emotion '{emotion}': {e}")
            return VoiceParameters(speed=1.0, pitch=1.0)
    
    async def detect_emotion_with_voice(self, user_message: str, context: str = "") -> Tuple[str, VoiceParameters]:
        """
        Detect emotion and return voice parameters in one call
        
        Args:
            user_message: The user's input message
            context: Optional conversation context
            
        Returns:
            Tuple of (emotion, voice_parameters)
        """
        emotion = await self.detect_emotion(user_message, context)
        voice_params = self.get_voice_parameters(emotion)
        return emotion, voice_params
    
    def _update_stats(self, emotion: str, detection_time: float):
        """Update performance statistics"""
        self.detection_stats["total_detections"] += 1
        
        # Update average response time
        total = self.detection_stats["total_detections"]
        current_avg = self.detection_stats["average_response_time"]
        self.detection_stats["average_response_time"] = (
            (current_avg * (total - 1) + detection_time) / total
        )
        
        # Update emotion frequency
        if emotion not in self.detection_stats["emotion_frequency"]:
            self.detection_stats["emotion_frequency"][emotion] = 0
        self.detection_stats["emotion_frequency"][emotion] += 1
    
    def get_emotion_mapping_info(self) -> Dict[str, Any]:
        """Get information about emotion-to-voice mapping"""
        return {
            "total_emotions": len(self.emotion_voice_map),
            "emotion_categories": {
                "positive": ["happy", "excited", "joyful", "enthusiastic", "elated"],
                "negative": ["sad", "disappointed", "melancholy", "dejected", "gloomy"],
                "anger": ["angry", "frustrated", "irritated", "furious", "annoyed"],
                "anxiety": ["worried", "anxious", "nervous", "concerned", "stressed"],
                "curiosity": ["curious", "interested", "intrigued", "fascinated", "wondering"],
                "calm": ["calm", "peaceful", "relaxed", "content", "serene"],
                "confusion": ["confused", "puzzled", "uncertain", "bewildered", "perplexed"],
                "surprise": ["surprised", "amazed", "astonished", "startled", "shocked"],
                "neutral": ["neutral", "indifferent", "apathetic", "detached", "bland"]
            },
            "voice_parameter_ranges": {
                "speed": {"min": 0.75, "max": 1.2, "default": 1.0},
                "pitch": {"min": 0.85, "max": 1.12, "default": 1.0}
            }
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "detection_performance": {
                "total_detections": self.detection_stats["total_detections"],
                "average_response_time": self.detection_stats["average_response_time"],
                "cache_size": len(self.detection_stats["voice_parameter_cache"])
            },
            "emotion_distribution": self.detection_stats["emotion_frequency"],
            "most_common_emotions": sorted(
                self.detection_stats["emotion_frequency"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5] if self.detection_stats["emotion_frequency"] else []
        }
    
    def clear_cache(self):
        """Clear performance cache"""
        self.detection_stats["voice_parameter_cache"].clear()
        logger.info("Emotion detector cache cleared")


class EmotionalResponseGenerator:
    """
    Generates responses using detected emotions for enhanced character behavior
    """
    
    def __init__(self, openai_key: Optional[str] = None):
        self.openai_key = openai_key
        
        # Character-specific response agent
        # Use cheap model instead of expensive gpt-4o
        openai_response_model = OpenAIModel("gpt-4o-mini")
        if openai_key:
            openai_response_model.api_key = openai_key
        
        self.response_agent = Agent(
            model=openai_response_model,
            system_prompt="""You are a character AI that responds naturally while embodying the detected emotion.

You will be given:
1. Character information (name, personality, profile)
2. Detected emotion from the user's message
3. The user's message
4. Conversation context

Respond as the character while naturally expressing the detected emotion through:
- Word choice and tone
- Speech patterns
- Emotional expressions
- Character-appropriate reactions

Be natural and authentic. Don't explicitly mention the emotion - just embody it naturally in your response."""
        )
    
    async def generate_emotional_response(
        self,
        character_name: str,
        character_personality: str,
        character_profile: str,
        detected_emotion: str,
        user_message: str,
        conversation_context: str = ""
    ) -> str:
        """
        Generate character response that naturally embodies the detected emotion
        
        Args:
            character_name: Name of the character
            character_personality: Character's personality description
            character_profile: Detailed character profile
            detected_emotion: Single word emotion detected from user
            user_message: The user's original message
            conversation_context: Previous conversation context
            
        Returns:
            Character response naturally embodying the emotion
        """
        try:
            # Prepare structured input
            prompt = f"""Character: {character_name}
Personality: {character_personality}
Profile: {character_profile}

Detected emotion from user: {detected_emotion}
User message: "{user_message}"

{f"Conversation context: {conversation_context}" if conversation_context else ""}

Respond as {character_name}, naturally embodying how they would react to someone feeling {detected_emotion}."""

            result = await self.response_agent.run(prompt)
            return str(result.data)
            
        except Exception as e:
            logger.error(f"Error generating emotional response: {e}")
            return f"I understand you're feeling {detected_emotion}. Let me help you with that."
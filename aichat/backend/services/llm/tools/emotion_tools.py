"""
Emotion detection and control tools for PydanticAI agents
"""

import logging
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_ai import Agent

from aichat.core.event_system import EventSeverity, EventType, get_event_system
from aichat.models.schemas import EmotionState

logger = logging.getLogger(__name__)


@dataclass
class EmotionPattern:
    """Pattern for emotion detection"""
    
    emotion: str
    keywords: List[str]
    regex_patterns: List[str]
    intensity_modifiers: Dict[str, float]


class EmotionDatabase:
    """Database of emotion patterns and rules"""
    
    def __init__(self):
        self.patterns = [
            EmotionPattern(
                emotion="happy",
                keywords=["happy", "excited", "joy", "great", "awesome", "wonderful", "amazing", "love", "fantastic", "brilliant", "perfect"],
                regex_patterns=[r"\b(yay|woo|hooray)\b", r"[!]{2,}", r"\b(so\s+good|very\s+nice)\b"],
                intensity_modifiers={"very": 0.3, "extremely": 0.5, "super": 0.4, "really": 0.2}
            ),
            EmotionPattern(
                emotion="sad",
                keywords=["sad", "sorry", "disappointed", "upset", "depressed", "down", "blue", "unhappy", "crying"],
                regex_patterns=[r"\b(oh\s+no|alas|sigh)\b", r"[.]{3,}", r"\b(feel\s+bad|so\s+sad)\b"],
                intensity_modifiers={"very": 0.3, "extremely": 0.5, "deeply": 0.4, "really": 0.2}
            ),
            EmotionPattern(
                emotion="angry",
                keywords=["angry", "mad", "frustrated", "annoyed", "furious", "irritated", "rage", "hate", "disgusted"],
                regex_patterns=[r"\b(damn|hell|argh|grr)\b", r"[!]{3,}", r"\b(so\s+mad|really\s+angry)\b"],
                intensity_modifiers={"very": 0.3, "extremely": 0.5, "really": 0.2, "absolutely": 0.4}
            ),
            EmotionPattern(
                emotion="surprised",
                keywords=["surprised", "wow", "amazing", "incredible", "shocking", "unexpected", "astonished", "stunned"],
                regex_patterns=[r"\b(whoa|omg|wow)\b", r"\b(no\s+way|can't\s+believe)\b", r"[?!]{2,}"],
                intensity_modifiers={"very": 0.3, "extremely": 0.5, "totally": 0.4, "completely": 0.5}
            ),
            EmotionPattern(
                emotion="confused",
                keywords=["confused", "don't understand", "not sure", "unclear", "puzzled", "bewildered", "perplexed"],
                regex_patterns=[r"\b(huh|what|eh)\?", r"\b(i\s+don't\s+get\s+it)\b", r"[?]{2,}"],
                intensity_modifiers={"very": 0.3, "completely": 0.5, "totally": 0.4, "really": 0.2}
            ),
            EmotionPattern(
                emotion="calm",
                keywords=["calm", "peaceful", "relaxed", "serene", "tranquil", "zen", "mellow", "chill"],
                regex_patterns=[r"\b(take\s+it\s+easy|no\s+worries)\b", r"\b(all\s+good|it's\s+fine)\b"],
                intensity_modifiers={"very": 0.3, "extremely": 0.4, "perfectly": 0.5, "quite": 0.2}
            ),
            EmotionPattern(
                emotion="excited",
                keywords=["excited", "thrilled", "pumped", "energetic", "enthusiastic", "eager", "hyped"],
                regex_patterns=[r"\b(let's\s+go|can't\s+wait)\b", r"[!]{1,}", r"\b(so\s+excited)\b"],
                intensity_modifiers={"very": 0.3, "extremely": 0.5, "super": 0.4, "really": 0.2}
            ),
            EmotionPattern(
                emotion="nervous",
                keywords=["nervous", "anxious", "worried", "scared", "afraid", "concerned", "uneasy", "tense"],
                regex_patterns=[r"\b(oh\s+dear|uh\s+oh)\b", r"\b(i'm\s+worried|kind\s+of\s+scared)\b"],
                intensity_modifiers={"very": 0.3, "extremely": 0.5, "quite": 0.2, "really": 0.2}
            )
        ]
    
    def detect_emotion(self, text: str) -> Tuple[str, float, str]:
        """
        Detect emotion from text with intensity and reasoning
        
        Returns:
            Tuple of (emotion, intensity, reasoning)
        """
        text_lower = text.lower()
        emotion_scores = {}
        reasoning_parts = []
        
        # Check each emotion pattern
        for pattern in self.patterns:
            score = 0.0
            matches = []
            
            # Check keywords
            for keyword in pattern.keywords:
                if keyword in text_lower:
                    score += 0.3
                    matches.append(f"keyword '{keyword}'")
            
            # Check regex patterns
            for regex_pattern in pattern.regex_patterns:
                if re.search(regex_pattern, text_lower):
                    score += 0.4
                    matches.append(f"pattern match")
            
            # Apply intensity modifiers
            base_intensity = 0.5
            for modifier, intensity_boost in pattern.intensity_modifiers.items():
                if modifier in text_lower:
                    base_intensity += intensity_boost
                    matches.append(f"intensity modifier '{modifier}'")
            
            if score > 0:
                final_score = min(score * base_intensity, 1.0)
                emotion_scores[pattern.emotion] = final_score
                if matches:
                    reasoning_parts.append(f"{pattern.emotion}: {', '.join(matches[:2])}")
        
        # Determine dominant emotion
        if not emotion_scores:
            return "neutral", 0.5, "No specific emotional indicators detected"
        
        dominant_emotion = max(emotion_scores.keys(), key=lambda k: emotion_scores[k])
        intensity = emotion_scores[dominant_emotion]
        reasoning = f"Detected {dominant_emotion} from: {'; '.join(reasoning_parts[:3])}"
        
        return dominant_emotion, intensity, reasoning


class EmotionTool:
    """Emotion analysis and control tool for PydanticAI agents"""
    
    def __init__(self):
        self.event_system = get_event_system()
        self.emotion_db = EmotionDatabase()
        self.emotion_transitions = {
            # Define natural emotion transitions and their probabilities
            "happy": {"excited": 0.3, "calm": 0.2, "surprised": 0.1},
            "sad": {"calm": 0.3, "angry": 0.2, "confused": 0.1},
            "angry": {"calm": 0.4, "sad": 0.2, "frustrated": 0.3},
            "excited": {"happy": 0.4, "nervous": 0.2, "surprised": 0.1},
            "confused": {"calm": 0.3, "nervous": 0.2, "sad": 0.1},
            "calm": {"happy": 0.2, "content": 0.3, "peaceful": 0.2},
            "nervous": {"calm": 0.4, "confused": 0.2, "worried": 0.3},
            "surprised": {"excited": 0.3, "confused": 0.2, "happy": 0.2}
        }
    
    def register_tools(self, agent: Agent, context_type):
        """Register emotion tools with PydanticAI agent"""
        
        @agent.tool
        async def detect_emotion(ctx: context_type, text: str) -> str:
            """Analyze text to detect emotional content and intensity
            
            Args:
                text: Text to analyze for emotional content
            """
            emotion, intensity, reasoning = self.emotion_db.detect_emotion(text)
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Emotion detected: {emotion}",
                {
                    "character": ctx.name,
                    "detected_emotion": emotion,
                    "intensity": intensity,
                    "reasoning": reasoning,
                    "analyzed_text": text[:100] + "..." if len(text) > 100 else text
                }
            )
            
            return f"Detected emotion: {emotion} (intensity: {intensity:.2f}). Reasoning: {reasoning}"
        
        @agent.tool
        async def change_emotion(ctx: context_type, emotion: str, intensity: float, reason: str) -> str:
            """Change the character's emotional state with validation and natural transitions
            
            Args:
                emotion: New emotion (happy, sad, excited, confused, angry, calm, nervous, surprised, etc.)
                intensity: Emotion intensity from 0.0 to 1.0
                reason: Why the emotion changed
            """
            if intensity < 0.0 or intensity > 1.0:
                return "Error: Intensity must be between 0.0 and 1.0"
            
            # Validate emotion transition
            current_emotion = ctx.emotion_state.emotion
            transition_valid = self._validate_emotion_transition(current_emotion, emotion)
            
            if not transition_valid and current_emotion != "neutral":
                suggested_emotions = list(self.emotion_transitions.get(current_emotion, {}).keys())
                return f"Warning: Sudden change from {current_emotion} to {emotion} may seem unnatural. Consider: {', '.join(suggested_emotions[:3])}"
            
            # Update emotion state
            ctx.emotion_state = EmotionState(
                emotion=emotion, 
                intensity=intensity, 
                context=reason
            )
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Character emotion changed to {emotion}",
                {
                    "character": ctx.name,
                    "previous_emotion": current_emotion,
                    "new_emotion": emotion,
                    "intensity": intensity,
                    "reason": reason,
                    "transition_natural": transition_valid
                }
            )
            
            return f"Emotion changed to {emotion} (intensity: {intensity:.2f}) because: {reason}"
        
        @agent.tool
        async def analyze_emotional_context(ctx: context_type, conversation_history: List[str] = None) -> str:
            """Analyze emotional patterns in conversation history
            
            Args:
                conversation_history: List of recent messages to analyze (optional)
            """
            if not conversation_history:
                conversation_history = [entry.get("details", "") for entry in ctx.conversation_history[-5:]]
            
            if not conversation_history:
                return "No conversation history available for emotional analysis"
            
            emotions_detected = []
            overall_tone = "neutral"
            
            for message in conversation_history:
                emotion, intensity, _ = self.emotion_db.detect_emotion(message)
                emotions_detected.append((emotion, intensity))
            
            if emotions_detected:
                # Calculate overall emotional tone
                emotion_counts = {}
                total_intensity = 0
                
                for emotion, intensity in emotions_detected:
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + intensity
                    total_intensity += intensity
                
                if emotion_counts:
                    overall_tone = max(emotion_counts.keys(), key=lambda k: emotion_counts[k])
                    avg_intensity = total_intensity / len(emotions_detected)
                    
                    analysis = f"Emotional analysis: Overall tone is {overall_tone} (avg intensity: {avg_intensity:.2f}). "
                    analysis += f"Emotions detected: {', '.join([f'{e}({i:.1f})' for e, i in emotions_detected[-3:]])}"
                    
                    await self.event_system.emit(
                        EventType.CHAT_MESSAGE,
                        f"Emotional context analyzed",
                        {
                            "character": ctx.name,
                            "overall_tone": overall_tone,
                            "average_intensity": avg_intensity,
                            "emotions_detected": len(emotions_detected),
                            "recent_emotions": emotions_detected[-3:]
                        }
                    )
                    
                    return analysis
            
            return "No clear emotional patterns detected in recent conversation"
        
        @agent.tool
        async def suggest_emotional_response(ctx: context_type, user_message: str, current_context: str = "") -> str:
            """Suggest appropriate emotional response based on user input and current state
            
            Args:
                user_message: The user's message to respond to
                current_context: Additional context about the conversation
            """
            # Detect user's emotion
            user_emotion, user_intensity, reasoning = self.emotion_db.detect_emotion(user_message)
            
            # Suggest appropriate character response emotion
            response_emotions = {
                "happy": ["happy", "excited", "joyful"],
                "sad": ["sympathetic", "caring", "gentle"],
                "angry": ["calm", "understanding", "diplomatic"],
                "excited": ["excited", "enthusiastic", "encouraging"],
                "confused": ["helpful", "patient", "clarifying"],
                "calm": ["calm", "peaceful", "supportive"],
                "nervous": ["reassuring", "comforting", "confident"],
                "surprised": ["curious", "interested", "engaged"]
            }
            
            suggested = response_emotions.get(user_emotion, ["neutral", "friendly"])
            current_emotion = ctx.emotion_state.emotion
            
            # Consider character's current emotional state
            recommendation = suggested[0]
            if current_emotion in ["sad", "angry"] and user_emotion == "happy":
                recommendation = "gradually_positive"  # Gradual emotional shift
            elif current_emotion == "excited" and user_emotion == "calm":
                recommendation = "moderately_calm"  # Tone down excitement
            
            suggestion_text = f"User shows {user_emotion} (intensity: {user_intensity:.2f}). "
            suggestion_text += f"Recommended response emotion: {recommendation}. "
            suggestion_text += f"Alternative emotions: {', '.join(suggested[1:3])}. "
            suggestion_text += f"Reasoning: {reasoning}"
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Emotional response suggested",
                {
                    "character": ctx.name,
                    "user_emotion": user_emotion,
                    "user_intensity": user_intensity,
                    "recommended_emotion": recommendation,
                    "alternatives": suggested[1:3],
                    "reasoning": reasoning
                }
            )
            
            return suggestion_text
    
    def _validate_emotion_transition(self, current: str, new: str) -> bool:
        """Check if emotion transition is natural"""
        if current == "neutral" or new == "neutral":
            return True
        
        if current in self.emotion_transitions:
            return new in self.emotion_transitions[current]
        
        return True  # Allow unknown transitions
    
    def get_emotion_for_voice(self, emotion_state: EmotionState) -> Dict[str, float]:
        """Convert emotion state to voice parameters"""
        emotion_to_voice = {
            "happy": {"speed": 1.1, "pitch": 1.1},
            "excited": {"speed": 1.2, "pitch": 1.2},
            "sad": {"speed": 0.8, "pitch": 0.9},
            "angry": {"speed": 1.0, "pitch": 1.1},
            "calm": {"speed": 0.9, "pitch": 1.0},
            "confused": {"speed": 0.9, "pitch": 0.95},
            "nervous": {"speed": 1.1, "pitch": 1.05},
            "surprised": {"speed": 1.15, "pitch": 1.15}
        }
        
        base_settings = emotion_to_voice.get(emotion_state.emotion, {"speed": 1.0, "pitch": 1.0})
        
        # Apply intensity scaling
        intensity_factor = emotion_state.intensity
        speed_adjustment = (base_settings["speed"] - 1.0) * intensity_factor + 1.0
        pitch_adjustment = (base_settings["pitch"] - 1.0) * intensity_factor + 1.0
        
        return {
            "speed": max(0.5, min(2.0, speed_adjustment)),
            "pitch": max(0.5, min(2.0, pitch_adjustment))
        }
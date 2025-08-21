"""
Voice control and TTS management tools for PydanticAI agents
"""

import logging
from typing import Dict, Optional, List
from enum import Enum

from pydantic import BaseModel
from pydantic_ai import Agent

from aichat.core.event_system import EventSeverity, EventType, get_event_system
from aichat.models.schemas import VoiceSettings, EmotionState

logger = logging.getLogger(__name__)


class VoiceEmotionProfile(str, Enum):
    """Predefined voice emotion profiles"""
    
    CHEERFUL = "cheerful"
    MELANCHOLY = "melancholy"
    ENERGETIC = "energetic"
    CALM = "calm"
    DRAMATIC = "dramatic"
    WHISPERY = "whispery"
    CONFIDENT = "confident"
    SHY = "shy"


class VoicePreset:
    """Voice preset configurations"""
    
    PRESETS = {
        VoiceEmotionProfile.CHEERFUL: {
            "speed": 1.1,
            "pitch": 1.15,
            "description": "Upbeat and positive tone"
        },
        VoiceEmotionProfile.MELANCHOLY: {
            "speed": 0.85,
            "pitch": 0.9,
            "description": "Slower, lower tone conveying sadness"
        },
        VoiceEmotionProfile.ENERGETIC: {
            "speed": 1.25,
            "pitch": 1.2,
            "description": "Fast and high energy"
        },
        VoiceEmotionProfile.CALM: {
            "speed": 0.9,
            "pitch": 0.95,
            "description": "Relaxed and peaceful"
        },
        VoiceEmotionProfile.DRAMATIC: {
            "speed": 0.95,
            "pitch": 1.1,
            "description": "Expressive and theatrical"
        },
        VoiceEmotionProfile.WHISPERY: {
            "speed": 0.8,
            "pitch": 0.85,
            "description": "Soft and intimate"
        },
        VoiceEmotionProfile.CONFIDENT: {
            "speed": 1.0,
            "pitch": 1.05,
            "description": "Strong and assured"
        },
        VoiceEmotionProfile.SHY: {
            "speed": 0.9,
            "pitch": 0.9,
            "description": "Quiet and hesitant"
        }
    }


class VoiceTool:
    """Voice control and TTS management tool for PydanticAI agents"""
    
    def __init__(self):
        self.event_system = get_event_system()
        self.voice_presets = VoicePreset()
        
        # Emotion to voice mapping
        self.emotion_voice_map = {
            "happy": VoiceEmotionProfile.CHEERFUL,
            "excited": VoiceEmotionProfile.ENERGETIC,
            "sad": VoiceEmotionProfile.MELANCHOLY,
            "angry": VoiceEmotionProfile.DRAMATIC,
            "calm": VoiceEmotionProfile.CALM,
            "confused": VoiceEmotionProfile.SHY,
            "nervous": VoiceEmotionProfile.SHY,
            "surprised": VoiceEmotionProfile.ENERGETIC,
            "neutral": VoiceEmotionProfile.CONFIDENT
        }
    
    def register_tools(self, agent: Agent, context_type):
        """Register voice tools with PydanticAI agent"""
        
        @agent.tool
        async def adjust_voice(ctx: context_type, speed: float = None, pitch: float = None) -> str:
            """Adjust voice settings for text-to-speech
            
            Args:
                speed: Speaking speed (0.5 to 2.0, default 1.0)
                pitch: Voice pitch (0.5 to 2.0, default 1.0)
            """
            if speed is not None:
                if speed < 0.5 or speed > 2.0:
                    return "Error: Speed must be between 0.5 and 2.0"
                ctx.voice_settings.speed = speed
            
            if pitch is not None:
                if pitch < 0.5 or pitch > 2.0:
                    return "Error: Pitch must be between 0.5 and 2.0"
                ctx.voice_settings.pitch = pitch
            
            await self.event_system.emit(
                EventType.SYSTEM_STATUS,
                f"Voice settings adjusted",
                {
                    "character": ctx.name,
                    "speed": ctx.voice_settings.speed,
                    "pitch": ctx.voice_settings.pitch,
                }
            )
            
            return f"Voice adjusted - Speed: {ctx.voice_settings.speed}, Pitch: {ctx.voice_settings.pitch}"
        
        @agent.tool
        async def apply_voice_preset(ctx: context_type, preset: str) -> str:
            """Apply a predefined voice emotion preset
            
            Args:
                preset: Voice preset name (cheerful, melancholy, energetic, calm, dramatic, whispery, confident, shy)
            """
            try:
                preset_enum = VoiceEmotionProfile(preset.lower())
                preset_config = self.voice_presets.PRESETS[preset_enum]
                
                ctx.voice_settings.speed = preset_config["speed"]
                ctx.voice_settings.pitch = preset_config["pitch"]
                
                await self.event_system.emit(
                    EventType.SYSTEM_STATUS,
                    f"Voice preset applied: {preset}",
                    {
                        "character": ctx.name,
                        "preset": preset,
                        "speed": preset_config["speed"],
                        "pitch": preset_config["pitch"],
                        "description": preset_config["description"]
                    }
                )
                
                return f"Applied {preset} voice preset: {preset_config['description']} (Speed: {preset_config['speed']}, Pitch: {preset_config['pitch']})"
                
            except ValueError:
                available_presets = [p.value for p in VoiceEmotionProfile]
                return f"Error: Unknown preset '{preset}'. Available presets: {', '.join(available_presets)}"
        
        @agent.tool
        async def sync_voice_with_emotion(ctx: context_type, auto_adjust: bool = True) -> str:
            """Automatically adjust voice settings based on current emotional state
            
            Args:
                auto_adjust: Whether to automatically adjust voice to match emotion
            """
            if not auto_adjust:
                return "Voice-emotion sync disabled. Voice settings remain manual."
            
            current_emotion = ctx.emotion_state.emotion
            intensity = ctx.emotion_state.intensity
            
            # Get base voice profile for emotion
            voice_profile = self.emotion_voice_map.get(current_emotion, VoiceEmotionProfile.CONFIDENT)
            base_settings = self.voice_presets.PRESETS[voice_profile]
            
            # Apply intensity scaling
            speed_base = base_settings["speed"]
            pitch_base = base_settings["pitch"]
            
            # Scale based on emotion intensity
            if intensity > 0.7:  # High intensity
                speed_multiplier = 1.1 if speed_base > 1.0 else 0.9
                pitch_multiplier = 1.1 if pitch_base > 1.0 else 0.9
            elif intensity < 0.3:  # Low intensity
                speed_multiplier = 0.95
                pitch_multiplier = 0.95
            else:  # Medium intensity
                speed_multiplier = 1.0
                pitch_multiplier = 1.0
            
            new_speed = max(0.5, min(2.0, speed_base * speed_multiplier))
            new_pitch = max(0.5, min(2.0, pitch_base * pitch_multiplier))
            
            ctx.voice_settings.speed = new_speed
            ctx.voice_settings.pitch = new_pitch
            
            await self.event_system.emit(
                EventType.SYSTEM_STATUS,
                f"Voice synced with emotion: {current_emotion}",
                {
                    "character": ctx.name,
                    "emotion": current_emotion,
                    "intensity": intensity,
                    "voice_profile": voice_profile.value,
                    "speed": new_speed,
                    "pitch": new_pitch,
                    "auto_adjusted": True
                }
            )
            
            return f"Voice synced with {current_emotion} emotion (intensity: {intensity:.2f}). Using {voice_profile.value} profile: Speed {new_speed:.2f}, Pitch {new_pitch:.2f}"
        
        @agent.tool
        async def get_voice_presets(ctx: context_type) -> str:
            """List all available voice presets with descriptions
            """
            preset_list = []
            for preset, config in self.voice_presets.PRESETS.items():
                preset_list.append(f"• {preset.value}: {config['description']} (Speed: {config['speed']}, Pitch: {config['pitch']})")
            
            result = "Available voice presets:\n" + "\n".join(preset_list)
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Voice presets requested",
                {
                    "character": ctx.name,
                    "presets_count": len(self.voice_presets.PRESETS)
                }
            )
            
            return result
        
        @agent.tool
        async def analyze_voice_for_text(ctx: context_type, text: str) -> str:
            """Analyze text and suggest optimal voice settings
            
            Args:
                text: Text to be spoken, analyze for optimal voice settings
            """
            text_lower = text.lower()
            suggested_speed = 1.0
            suggested_pitch = 1.0
            reasoning = []
            
            # Analyze text characteristics
            if "!" in text or text.isupper():
                suggested_speed = 1.1
                suggested_pitch = 1.15
                reasoning.append("exclamatory content")
            
            if "?" in text:
                suggested_pitch = 1.1
                reasoning.append("questioning tone")
            
            if len(text) > 200:
                suggested_speed = 0.95
                reasoning.append("long text, slower for clarity")
            
            # Check for emotional keywords
            if any(word in text_lower for word in ["whisper", "quiet", "soft"]):
                suggested_speed = 0.8
                suggested_pitch = 0.85
                reasoning.append("soft/quiet indicators")
            
            if any(word in text_lower for word in ["shout", "loud", "yell"]):
                suggested_speed = 1.2
                suggested_pitch = 1.2
                reasoning.append("loud/emphatic indicators")
            
            if any(word in text_lower for word in ["slow", "careful", "think"]):
                suggested_speed = 0.85
                reasoning.append("thoughtful/careful content")
            
            reasoning_text = ", ".join(reasoning) if reasoning else "standard speech patterns"
            
            analysis = f"Voice analysis for text: Suggested Speed: {suggested_speed:.2f}, Pitch: {suggested_pitch:.2f}. "
            analysis += f"Reasoning: {reasoning_text}. "
            analysis += f"Text length: {len(text)} characters."
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Voice analysis completed",
                {
                    "character": ctx.name,
                    "text_length": len(text),
                    "suggested_speed": suggested_speed,
                    "suggested_pitch": suggested_pitch,
                    "reasoning": reasoning_text
                }
            )
            
            return analysis
        
        @agent.tool
        async def create_custom_voice_profile(ctx: context_type, name: str, speed: float, pitch: float, description: str = "") -> str:
            """Create a custom voice profile for later use
            
            Args:
                name: Name for the custom profile
                speed: Speed setting (0.5 to 2.0)
                pitch: Pitch setting (0.5 to 2.0)
                description: Optional description of the profile
            """
            if speed < 0.5 or speed > 2.0:
                return "Error: Speed must be between 0.5 and 2.0"
            
            if pitch < 0.5 or pitch > 2.0:
                return "Error: Pitch must be between 0.5 and 2.0"
            
            # Store in character's voice settings (this would be expanded to save to database)
            profile_name = f"custom_{name.lower().replace(' ', '_')}"
            
            # Apply the new profile immediately
            ctx.voice_settings.speed = speed
            ctx.voice_settings.pitch = pitch
            ctx.voice_settings.voice_model = profile_name
            
            await self.event_system.emit(
                EventType.SYSTEM_STATUS,
                f"Custom voice profile created: {name}",
                {
                    "character": ctx.name,
                    "profile_name": profile_name,
                    "speed": speed,
                    "pitch": pitch,
                    "description": description
                }
            )
            
            return f"Created custom voice profile '{name}' with Speed: {speed}, Pitch: {pitch}. {description if description else ''} Profile applied immediately."
    
    def get_voice_settings_for_emotion(self, emotion_state: EmotionState) -> VoiceSettings:
        """Get optimal voice settings for an emotion state"""
        emotion = emotion_state.emotion
        intensity = emotion_state.intensity
        
        # Get base voice profile
        voice_profile = self.emotion_voice_map.get(emotion, VoiceEmotionProfile.CONFIDENT)
        base_settings = self.voice_presets.PRESETS[voice_profile]
        
        # Apply intensity scaling
        speed_base = base_settings["speed"]
        pitch_base = base_settings["pitch"]
        
        # Scale based on emotion intensity
        if intensity > 0.7:  # High intensity
            speed_multiplier = 1.1 if speed_base > 1.0 else 0.9
            pitch_multiplier = 1.1 if pitch_base > 1.0 else 0.9
        elif intensity < 0.3:  # Low intensity
            speed_multiplier = 0.95
            pitch_multiplier = 0.95
        else:  # Medium intensity
            speed_multiplier = 1.0
            pitch_multiplier = 1.0
        
        final_speed = max(0.5, min(2.0, speed_base * speed_multiplier))
        final_pitch = max(0.5, min(2.0, pitch_base * pitch_multiplier))
        
        return VoiceSettings(
            speed=final_speed,
            pitch=final_pitch,
            voice_model=voice_profile.value
        )
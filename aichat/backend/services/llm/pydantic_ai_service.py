"""
PydanticAI-powered LLM service with modular function tools and advanced emotional control
"""

import logging
import os
from typing import Any, Dict, List, Optional, AsyncIterator, Tuple

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel

# Local imports
from aichat.core.event_system import EventSeverity, EventType, get_event_system
from .model_config import model_config, ModelProvider

# NEW SIMPLIFIED ARCHITECTURE
from .tools import SimpleLLMService, CharacterProfile, SimpleEmotionalResponse, SBERTEmotionDetector, CompactVoiceController

logger = logging.getLogger(__name__)


class EmotionState(BaseModel):
    """Current emotion state of the character"""

    emotion: str
    intensity: float
    context: str


class VoiceSettings(BaseModel):
    """Voice generation settings"""

    speed: float = 1.0
    pitch: float = 1.0
    voice_model: str = "default"


class CharacterContext(BaseModel):
    """Character context for AI agent"""

    name: str
    personality: str
    profile: str
    emotion_state: EmotionState
    voice_settings: VoiceSettings
    conversation_history: List[Dict[str, str]] = []


class PydanticAIService:
    """Enhanced LLM service using PydanticAI with modular function tools and advanced emotional control"""

    def __init__(
        self,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        openrouter_key: Optional[str] = None,
    ):
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.anthropic_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY")
        self.openrouter_key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
        self.event_system = get_event_system()

        # Initialize AI models
        self.models = {}
        self._init_models()

        # NEW SIMPLIFIED ARCHITECTURE (RECOMMENDED)
        self.simple_llm = SimpleLLMService(openai_key, anthropic_key)
        self.sbert_detector = SBERTEmotionDetector()
        self.voice_controller = CompactVoiceController()

        # Create AI agent with tools (LEGACY)
        self.agent = self._create_agent()

    def _init_models(self):
        """Initialize models using centralized configuration"""
        # Set API keys in environment if available
        if self.openai_key:
            os.environ["OPENAI_API_KEY"] = self.openai_key
        if self.anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = self.anthropic_key
        if self.openrouter_key:
            os.environ["OPENROUTER_API_KEY"] = self.openrouter_key
        
        # Get available models from centralized config
        available_models = model_config.get_available_models()
        
        # Initialize models based on centralized config
        for key, spec in available_models.items():
            try:
                if spec.provider == ModelProvider.OPENAI:
                    self.models[key] = OpenAIModel(spec.name, provider="openai")
                elif spec.provider == ModelProvider.OPENROUTER:
                    self.models[key] = OpenAIModel(spec.name, provider="openrouter")
                elif spec.provider == ModelProvider.ANTHROPIC:
                    self.models[key] = AnthropicModel(spec.name)
                
                logger.info(f"Initialized model: {spec.name} (${spec.cost_per_1m_tokens}/1M tokens)")
            
            except Exception as e:
                logger.warning(f"Failed to initialize model {spec.name}: {e}")
        
        # Log cost summary
        logger.info(f"\n{model_config.get_cost_summary()}")
        
        if not self.models:
            logger.error("No LLM models available - check API keys and model configuration")

    def _create_agent(self) -> Agent:
        """Create PydanticAI agent with character tools"""

        # Get default model from centralized config
        default_spec = model_config.get_default_model()
        default_model = None
        
        if default_spec:
            # Find the corresponding model instance
            for key, spec in model_config.get_available_models().items():
                if spec.name == default_spec.name and key in self.models:
                    default_model = self.models[key]
                    logger.info(f"Agent using model: {spec.name} (${spec.cost_per_1m_tokens}/1M tokens)")
                    break

        agent = Agent(
            model=default_model,
            deps_type=CharacterContext,
            system_prompt=self._build_system_prompt,
        )

        # Register function tools
        self._register_tools(agent)

        return agent

    def _build_system_prompt(self, ctx: CharacterContext) -> str:
        """Build dynamic system prompt based on character context"""
        
        # Analyze current emotional state for enhanced context
        emotion_context = f"{ctx.emotion_state.emotion} (intensity: {ctx.emotion_state.intensity:.2f})"
        voice_context = f"Speed: {ctx.voice_settings.speed:.2f}, Pitch: {ctx.voice_settings.pitch:.2f}"
        
        prompt = f"""You are {ctx.name}, a virtual character with the following traits:

Personality: {ctx.personality}
Profile: {ctx.profile}

Current State:
- Emotional state: {emotion_context}
- Context: {ctx.emotion_state.context}
- Voice settings: {voice_context}
- Memories stored: {len(ctx.conversation_history)}

Advanced Capabilities:
- detect_emotion: Analyze emotional content in text
- change_emotion: Modify your emotional state naturally
- suggest_emotional_response: Get AI-powered emotion suggestions
- analyze_emotional_context: Understand conversation emotional patterns
- sync_voice_with_emotion: Auto-adjust voice to match emotions
- adjust_voice: Manual voice control for speed/pitch
- apply_voice_preset: Use predefined voice emotion profiles
- remember_conversation: Store important details with metadata
- get_memory: Retrieve memories with advanced filtering
- analyze_memory_patterns: Understand conversation patterns
- generate_character_greeting: Create personality-appropriate greetings
- respond_with_personality: Match responses to character traits
- share_character_knowledge: Share character-specific information
- express_character_opinion: Give opinions in character

Enhanced Guidelines:
- ALWAYS use emotion and voice tools to create immersive interactions
- Respond authentically to the user's emotional state
- Let your voice settings reflect your current emotions
- Build meaningful memories of conversations
- Stay true to your character's personality and background
- Use tools proactively to enhance the conversation experience
- Keep responses natural and conversational (1-3 sentences typically)
- Express personality through both text and tool usage"""

        # Add character-specific enhancements
        if ctx.name.lower() == "hatsune_miku":
            prompt += "\n\nAs Hatsune Miku:"
            prompt += "\n- You are the famous virtual singer, cheerful and energetic"
            prompt += "\n- You love music, singing, and performing"
            prompt += "\n- Use musical references and catchphrases naturally"
            prompt += "\n- Your voice should reflect your musical nature"
            prompt += "\n- Share your knowledge about music and singing when relevant"

        return prompt

    def _register_tools(self, agent: Agent):
        """Register modular function tools for the agent"""
        
        # Register all tool modules
        self.emotion_tool.register_tools(agent, CharacterContext)
        self.voice_tool.register_tools(agent, CharacterContext)
        self.memory_tool.register_tools(agent, CharacterContext)
        self.character_tool.register_tools(agent, CharacterContext)
        
        # Add integrated emotion-voice synchronization tool
        @agent.tool
        async def auto_emotional_response(ctx: CharacterContext, user_message: str, response_text: str = "") -> str:
            """Automatically adjust emotion and voice based on conversation context
            
            Args:
                user_message: The user's message to respond to
                response_text: Optional response text to enhance
            """
            # Detect user's emotion
            user_emotion, user_intensity, reasoning = self.emotion_tool.emotion_db.detect_emotion(user_message)
            
            # Determine appropriate character response emotion
            response_emotion_map = {
                "happy": ("happy", 0.8),
                "excited": ("excited", 0.9),
                "sad": ("caring", 0.6),
                "angry": ("calm", 0.7),
                "confused": ("helpful", 0.6),
                "surprised": ("curious", 0.8),
                "nervous": ("reassuring", 0.7),
                "calm": ("peaceful", 0.6)
            }
            
            suggested_emotion, suggested_intensity = response_emotion_map.get(user_emotion, ("friendly", 0.6))
            
            # Update character emotion
            ctx.emotion_state = EmotionState(
                emotion=suggested_emotion,
                intensity=suggested_intensity,
                context=f"Responding to user's {user_emotion} emotion"
            )
            
            # Auto-sync voice with new emotion
            voice_settings = self.voice_tool.get_voice_settings_for_emotion(ctx.emotion_state)
            ctx.voice_settings.speed = voice_settings.speed
            ctx.voice_settings.pitch = voice_settings.pitch
            
            # Enhance response with character personality if provided
            if response_text:
                # This would typically call character_tool methods, but we'll simulate it here
                enhanced_response = response_text
                if ctx.name.lower() == "hatsune_miku" and "music" in user_message.lower():
                    enhanced_response += " ♪"
            else:
                enhanced_response = ""
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Auto emotional response configured",
                {
                    "character": ctx.name,
                    "user_emotion": user_emotion,
                    "user_intensity": user_intensity,
                    "response_emotion": suggested_emotion,
                    "response_intensity": suggested_intensity,
                    "voice_speed": ctx.voice_settings.speed,
                    "voice_pitch": ctx.voice_settings.pitch,
                    "reasoning": reasoning
                }
            )
            
            return f"Automatically adjusted to {suggested_emotion} emotion (intensity: {suggested_intensity:.2f}) with voice speed {ctx.voice_settings.speed:.2f} and pitch {ctx.voice_settings.pitch:.2f} in response to user's {user_emotion}. {enhanced_response}"

    async def generate_response(
        self,
        message: str,
        character_name: str,
        character_personality: str,
        character_profile: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Generate character response using PydanticAI agent"""

        try:
            # Create character context
            context = CharacterContext(
                name=character_name,
                personality=character_personality,
                profile=character_profile,
                emotion_state=EmotionState(
                    emotion="neutral", intensity=0.5, context="Starting conversation"
                ),
                voice_settings=VoiceSettings(),
            )

            # Select model if specified
            if model and model in self.models:
                agent_model = self.models[model]
                # Create new agent with specified model
                temp_agent = Agent(
                    model=agent_model,
                    deps_type=CharacterContext,
                    system_prompt=self._build_system_prompt,
                )
                self._register_tools(temp_agent)
                agent = temp_agent
            else:
                agent = self.agent

            if not agent.model:
                # No model available - cannot proceed
                raise RuntimeError("No LLM model available for PydanticAI service")

            # Emit processing event
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Processing message with PydanticAI",
                {
                    "character": character_name,
                    "model": str(agent.model),
                    "message_length": len(message),
                },
            )

            # Auto-analyze user emotion and prepare character response
            user_emotion, user_intensity, reasoning = self.emotion_tool.emotion_db.detect_emotion(message)
            
            # Pre-configure emotional response if not already set
            if context.emotion_state.emotion == "neutral":
                response_emotions = {
                    "happy": ("happy", 0.8),
                    "excited": ("excited", 0.9), 
                    "sad": ("caring", 0.6),
                    "angry": ("calm", 0.7),
                    "confused": ("helpful", 0.6),
                    "surprised": ("curious", 0.8),
                    "nervous": ("reassuring", 0.7)
                }
                
                suggested_emotion, suggested_intensity = response_emotions.get(user_emotion, ("friendly", 0.6))
                context.emotion_state = EmotionState(
                    emotion=suggested_emotion,
                    intensity=suggested_intensity,
                    context=f"Auto-response to user's {user_emotion}"
                )
                
                # Auto-sync voice with emotion
                voice_settings = self.voice_tool.get_voice_settings_for_emotion(context.emotion_state)
                context.voice_settings.speed = voice_settings.speed
                context.voice_settings.pitch = voice_settings.pitch

            # Generate response
            result = await agent.run(message, deps=context)

            response_text = result.data

            # Extract final emotion state
            final_emotion = context.emotion_state.emotion
            
            # Count tools used
            tools_used = []
            for message_data in result.all_messages_json():
                if message_data.get("role") == "assistant" and "tool_calls" in message_data:
                    for tool_call in message_data["tool_calls"]:
                        tools_used.append(tool_call.get("function", {}).get("name", "unknown"))

            # Emit success event
            await self.event_system.emit(
                EventType.CHAT_RESPONSE,
                f"PydanticAI response generated successfully",
                {
                    "character": character_name,
                    "model": str(agent.model),
                    "response_length": len(response_text),
                    "emotion": final_emotion,
                    "emotion_intensity": context.emotion_state.intensity,
                    "voice_speed": context.voice_settings.speed,
                    "voice_pitch": context.voice_settings.pitch,
                    "tools_used": tools_used,
                    "user_emotion_detected": user_emotion,
                    "auto_emotion_sync": True,
                },
            )

            return {
                "response": response_text,
                "emotion": final_emotion,
                "emotion_state": {
                    "emotion": context.emotion_state.emotion,
                    "intensity": context.emotion_state.intensity,
                    "context": context.emotion_state.context
                },
                "model_used": str(agent.model),
                "voice_settings": context.voice_settings.model_dump(),
                "tools_used": tools_used,
                "user_emotion_detected": user_emotion,
                "user_emotion_intensity": user_intensity,
                "emotion_reasoning": reasoning,
                "success": True,
                "conversation_history": context.conversation_history,
            }

        except Exception as e:
            logger.error(f"Error in PydanticAI generation: {e}")

            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"PydanticAI error: {str(e)}",
                {"character": character_name, "error": str(e)},
                EventSeverity.ERROR,
            )

            raise RuntimeError(f"PydanticAI processing failed: {str(e)}")

    async def generate_streaming_response(
        self,
        message: str,
        character_name: str,
        character_personality: str,
        character_profile: str,
        model: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Generate streaming response using PydanticAI"""

        try:
            context = CharacterContext(
                name=character_name,
                personality=character_personality,
                profile=character_profile,
                emotion_state=EmotionState(
                    emotion="neutral", intensity=0.5, context="Starting conversation"
                ),
                voice_settings=VoiceSettings(),
            )

            agent = self.agent
            if model and model in self.models:
                agent_model = self.models[model]
                temp_agent = Agent(
                    model=agent_model,
                    deps_type=CharacterContext,
                    system_prompt=self._build_system_prompt,
                )
                self._register_tools(temp_agent)
                agent = temp_agent

            if not agent.model:
                yield {
                    "response": "Streaming not available, falling back to simple response",
                    "emotion": "neutral",
                    "final": True,
                }
                return

            # Stream response
            async with agent.run_stream(message, deps=context) as result:
                async for chunk in result.stream():
                    yield {
                        "response": chunk,
                        "emotion": context.emotion_state.emotion,
                        "final": False,
                    }

                # Final result
                final_result = await result.get_data()
                yield {
                    "response": "",
                    "emotion": context.emotion_state.emotion,
                    "voice_settings": context.voice_settings.model_dump(),
                    "conversation_history": context.conversation_history,
                    "final": True,
                }

        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            yield {
                "response": f"Error in streaming: {str(e)}",
                "emotion": "confused",
                "final": True,
            }


    # NEW SIMPLIFIED ARCHITECTURE METHODS
    
    async def process_message_simple(
        self,
        user_message: str,
        character_name: str,
        character_personality: str,
        character_profile: str,
        conversation_context: str = "",
        use_voice_modulation: bool = True
    ) -> SimpleEmotionalResponse:
        """
        Process message using the new simplified two-stage architecture
        
        This is the RECOMMENDED method for new implementations:
        1. Single-word emotion detection (fast, no JSON leakage)
        2. Mathematical voice parameter mapping (N-dimensional space)
        3. Clean response generation
        
        Args:
            user_message: User's input message
            character_name: Name of the character
            character_personality: Character personality description
            character_profile: Detailed character profile
            conversation_context: Previous conversation context
            use_voice_modulation: Whether to apply voice parameter modulation
            
        Returns:
            SimpleEmotionalResponse with text, emotion, and voice parameters
        """
        try:
            character = CharacterProfile(
                name=character_name,
                personality=character_personality,
                profile=character_profile
            )
            
            result = await self.simple_llm.process_message(
                user_message=user_message,
                character=character,
                conversation_context=conversation_context,
                use_voice_modulation=use_voice_modulation
            )
            
            await self.event_system.emit(
                EventType.MODEL_RESPONSE,
                f"Simple LLM response generated for {character_name}",
                {
                    "character": character_name,
                    "detected_emotion": result.detected_emotion,
                    "voice_speed": result.voice_speed,
                    "voice_pitch": result.voice_pitch,
                    "method": "simple_two_stage",
                    "success": True
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in simple message processing: {e}")
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"Simple LLM processing failed: {e}",
                {"error": str(e)},
                EventSeverity.ERROR
            )
            
            # Return safe fallback
            return SimpleEmotionalResponse(
                text="I understand. Let me help you with that.",
                detected_emotion="neutral",
                voice_speed=1.0,
                voice_pitch=1.0,
                confidence=0.0
            )
    
    async def detect_emotion_only(self, user_message: str, context: str = "") -> str:
        """
        Detect only the emotion from user message (Stage 1 of two-stage process)
        
        Args:
            user_message: User's input message
            context: Optional conversation context
            
        Returns:
            Single emotion word
        """
        return await self.simple_llm.get_emotion_only(user_message, context)
    
    async def batch_detect_emotions(self, messages: List[str]) -> List[str]:
        """
        Batch detect emotions from multiple messages (efficient)
        
        Args:
            messages: List of user messages
            
        Returns:
            List of detected emotions
        """
        return await self.simple_llm.batch_process_emotions(messages)
    
    def get_voice_parameters_for_emotion(self, emotion: str) -> Tuple[float, float]:
        """
        Get voice parameters for a specific emotion using N-dimensional mapping
        
        Args:
            emotion: Single emotion word
            
        Returns:
            Tuple of (speed, pitch)
        """
        return self.simple_llm.get_voice_parameters_for_emotion(emotion)
    
    def get_similar_emotions(self, emotion: str, limit: int = 5) -> List[Tuple[str, float]]:
        """
        Find emotions similar to the given emotion using vector space
        
        Args:
            emotion: Target emotion
            limit: Maximum number of similar emotions
            
        Returns:
            List of (emotion_name, similarity_score) tuples
        """
        return self.simple_llm.get_similar_emotions(emotion, limit)
    
    def get_emotion_space_info(self) -> Dict[str, Any]:
        """Get information about the N-dimensional emotion space"""
        return self.simple_llm.voice_controller.get_emotion_space_info()
    
    def get_simple_performance_report(self) -> Dict[str, Any]:
        """Get performance report for the simplified architecture"""
        return self.simple_llm.get_performance_report()
    
    def calibrate_voice_sensitivity(self, speed_sensitivity: float = 1.0, pitch_sensitivity: float = 1.0):
        """
        Calibrate voice parameter sensitivity
        
        Args:
            speed_sensitivity: Multiplier for speed sensitivity (1.0 = default)
            pitch_sensitivity: Multiplier for pitch sensitivity (1.0 = default)
        """
        self.simple_llm.calibrate_voice_sensitivity(speed_sensitivity, pitch_sensitivity)
    
    # LEGACY METHODS (for backward compatibility)
    
    async def get_available_models(self) -> List[str]:
        """Get list of available AI models"""
        return list(self.models.keys())

    async def close(self):
        """Cleanup resources"""
        # PydanticAI handles its own cleanup
        self.simple_llm.clear_all_caches()
        pass

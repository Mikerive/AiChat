"""
Unified LLM Service with Memory Integration

This is the single, clean implementation for all LLM interactions.
Integrates with the conversation memory system for context management.
"""

import logging
import os
from typing import Any, Dict, Optional
import aiohttp

from .memory import MemoryManager, CompressedContext
from .analysis_model import analyze_for_response, ResponseMetadata
from aichat.core.event_system import EventSeverity, EventType, get_event_system
from .model_config import model_config

logger = logging.getLogger(__name__)


class LLMService:
    """Unified LLM service with memory-aware context management"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize LLM service with OpenRouter"""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.event_system = get_event_system()
        self.memory_manager = MemoryManager()
        
        # Get default model from centralized config
        default_spec = model_config.get_default_model()
        if not default_spec:
            logger.error("No OpenRouter models available - API key not set")
            self.default_model = None
        else:
            self.default_model = default_spec.name
            logger.info(f"LLM Service using: {self.default_model} (${default_spec.cost_per_1m_tokens}/1M tokens)")
        
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aichat.local",
                "X-Title": "AiChat Application",
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def generate_response(
        self,
        message: str,
        session_id: str,
        user_id: str,
        character_id: int,
        character_name: str,
        character_personality: str,
        character_profile: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """
        Generate character response with memory-aware context
        
        This method:
        1. Gets or creates a conversation session
        2. Adds the user's turn to memory
        3. Gets compressed context if needed
        4. Generates response with full context
        5. Adds assistant's turn to memory
        6. Returns response with metadata
        """
        
        try:
            if not self.api_key:
                logger.error("OpenRouter API key not configured")
                raise RuntimeError("OpenRouter API key is required but not configured")
            
            # Get or create conversation session
            session = await self.memory_manager.get_or_create_session(
                user_id=user_id,
                character_id=character_id,
                character_name=character_name
            )
            
            # Add user's turn to memory
            await self.memory_manager.add_turn(
                session_id=session.session_id,
                speaker_id=user_id,
                speaker_type="user",
                message=message,
                metadata={"timestamp": "now"}
            )
            
            # Get current context (may trigger compression)
            context = await self.memory_manager.get_session_context(session.session_id)
            
            # STEP 1: Analyze conversation for all metadata BEFORE generating response
            conversation_context = self._get_recent_context(context)
            metadata = await analyze_for_response(
                user_message=message,
                character_name=character_name,
                character_personality=character_personality,
                conversation_context=conversation_context,
                memory_manager=self.memory_manager,
                session_id=session.session_id
            )
            
            # STEP 2: Build system prompt with analysis metadata
            system_prompt = self._build_contextual_prompt(
                context=context,
                character_name=character_name,
                character_personality=character_personality,
                character_profile=character_profile,
                metadata=metadata
            )
            
            # STEP 3: Generate main response
            model_name = model or self.default_model
            if not model_name:
                raise RuntimeError("No model available for generation")
            
            
            # Log context usage
            logger.info(f"Using context with {len(context.recent_turns)} recent turns, "
                       f"{len(context.preserved_turns)} preserved turns")
            
            # Make simple API request - no tools needed (memory handled by analysis model)
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Make API request  
            session_http = await self._get_session()
            async with session_http.post(
                f"{self.base_url}/chat/completions", json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error {response.status}: {error_text}")
                    raise RuntimeError(f"OpenRouter API error: {response.status} - {error_text}")
                
                result = await response.json()
                
                if "choices" not in result or len(result["choices"]) == 0:
                    raise ValueError("No response choices in API result")
                
                final_response = result["choices"][0]["message"]["content"]
                if not final_response:
                    raise ValueError("No content in API response")
            
            # Use the pre-analyzed metadata (much more comprehensive)
            emotion = metadata.emotion
            
            # Clean response
            cleaned_response = self._clean_response(final_response)
            
            # Add assistant's turn to memory with rich metadata
            assistant_metadata = metadata.to_dict()
            assistant_metadata.update({
                "model_used": model_name,
                "analysis_model_used": True,
                "tool_calls_made": True  # Flag that tools were available
            })
            
            await self.memory_manager.add_turn(
                session_id=session.session_id,
                speaker_id=character_name,
                speaker_type="assistant",
                message=cleaned_response,
                metadata=assistant_metadata
            )
            
            # Emit success event
            await self.event_system.emit(
                EventType.CHAT_RESPONSE,
                f"Response generated with memory context",
                {
                    "session_id": session.session_id,
                    "character": character_name,
                    "model": model_name,
                    "emotion": emotion,
                    "context_turns": len(context.recent_turns) + len(context.preserved_turns),
                    "compression_count": session.compression_count
                }
            )
            
            return {
                "response": cleaned_response,
                "emotion": emotion,
                "intensity": metadata.intensity,
                "response_tone": metadata.response_tone,
                "energy_level": metadata.energy_level,
                "voice_params": metadata.voice_params.to_dict(),
                "conversation_analysis": metadata.conversation_analysis.to_dict(),
                "model_used": model_name,
                "session_id": session.session_id,
                "turn_number": session.total_turns,
                "success": True
            }
                    
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"LLM processing error: {str(e)}",
                {"character": character_name, "error": str(e)},
                EventSeverity.ERROR,
            )
            raise RuntimeError(f"LLM processing failed: {str(e)}")
    
    def _build_contextual_prompt(
        self,
        context: CompressedContext,
        character_name: str,
        character_personality: str,
        character_profile: str,
        metadata: Optional[ResponseMetadata] = None
    ) -> str:
        """Build system prompt with compressed context"""
        
        # If we have a compressed context with character reminder, use it
        if context and context.character_reminder:
            # Context already has character information
            return context.to_prompt()
        
        # Extract metadata values
        if metadata:
            emotion = metadata.emotion
            intensity = metadata.intensity
            tone = metadata.response_tone
            energy = metadata.energy_level
            memory_context = metadata.memory_context
        else:
            emotion = "neutral"
            intensity = 0.5
            tone = "casual"
            energy = "medium"
            memory_context = []
        
        # Otherwise, build fresh prompt (first message in session)
        base_prompt = f"""You are {character_name}.

PERSONALITY: {character_personality}
BACKGROUND: {character_profile}

RESPONSE GUIDANCE:
- EMOTION: {emotion} (intensity: {intensity}/1.0)
- TONE: {tone}
- ENERGY LEVEL: {energy}

Please respond as {character_name} would, staying true to your personality and background.

Express your current emotional state ({emotion}) with {intensity} intensity through:
- Word choice matching the {tone} tone
- {energy} energy level in your response
- Natural reactions to the user's message
- Body language or actions if appropriate

Remember:
- Stay in character at all times
- Show authentic {emotion} emotion at {intensity} intensity
- Match the {tone} tone naturally
- Respond with {energy} energy level
- Keep responses conversational and engaging"""

        # Add memory context if provided by analysis model
        if memory_context:
            memory_section = self._format_memory_context(memory_context)
            base_prompt += f"\n\n{memory_section}"
        
        # Add any context if available
        if context and (context.recent_turns or context.preserved_turns):
            base_prompt += "\n\n" + context.to_prompt()
        
        return base_prompt
    
    def _format_memory_context(self, memory_results: list) -> str:
        """Format memory search results for the character model"""
        if not memory_results:
            return ""
        
        memory_section = "RELEVANT MEMORIES:\n"
        memory_section += "Your analysis has surfaced these relevant past conversation moments:\n\n"
        
        for turn in memory_results:
            speaker = "User" if turn.speaker_type == "user" else turn.speaker_id
            memory_section += f"• Turn {turn.turn_id} ({speaker}): \"{turn.message}\"\n"
        
        memory_section += "\nUse these memories naturally in your response when relevant."
        return memory_section
    
    def _get_recent_context(self, context: CompressedContext) -> str:
        """Extract recent conversation for emotion detection"""
        if not context or not context.recent_turns:
            return ""
        
        # Get last few exchanges for context
        recent_messages = []
        for turn in context.recent_turns[-6:]:  # Last 6 turns (3 exchanges)
            speaker = "User" if turn.speaker_type == "user" else turn.speaker_id
            recent_messages.append(f"{speaker}: {turn.message}")
        
        return "\n".join(recent_messages)
    
    def _extract_emotion(self, response: str) -> str:
        """
        Fallback emotion extraction from response text.
        This is rarely used since we now detect emotion beforehand.
        """
        from .emotion_detector import get_emotion_detector
        detector = get_emotion_detector()
        return detector.extract_emotion_from_text(response)
    
    def _clean_response(self, response: str) -> str:
        """Clean up response text"""
        # Remove emotion markers
        import re
        cleaned = re.sub(r'\[(\w+)\]', '', response)
        
        # Remove excessive whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
    
    async def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of a conversation session"""
        return await self.memory_manager.get_session_summary(session_id)
    
    async def search_conversation_history(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> list:
        """Search through conversation history"""
        return await self.memory_manager.search_memories(query, session_id)
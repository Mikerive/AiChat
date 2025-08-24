"""
Chat service for handling character conversations and TTS generation
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List

# Local imports
from aichat.constants.paths import GENERATED_AUDIO_DIR, ensure_dirs
from aichat.core.database import Character, db_ops
from aichat.core.event_system import EventSeverity, EventType, get_event_system
from aichat.models.schemas import CharacterResponse, ChatResponse

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling character conversations and TTS generation"""
    
    def __init__(self):
        """Initialize chat service"""
        self._current_character_id: Optional[int] = None
        self._llm_service = None  # Unified LLM service with memory
        self._tts_service = None
        self._event_system = get_event_system()
        self._current_session_id: Optional[str] = None  # Track current session
        self._current_user_id: str = "default_user"  # Default user ID
        
        # Ensure audio directories exist
        ensure_dirs(GENERATED_AUDIO_DIR)
        
        logger.info("ChatService initialized with memory support")
    
    async def get_current_character(self) -> Optional[Dict[str, Any]]:
        """Get the current active character"""
        try:
            if self._current_character_id is None:
                # Try to get the first character as default
                characters = await db_ops.list_characters()
                if characters:
                    self._current_character_id = characters[0].id
                else:
                    return None
            
            character = await db_ops.get_character(self._current_character_id)
            if character:
                return {
                    "id": character.id,
                    "name": character.name,
                    "profile": character.profile,
                    "personality": character.personality,
                    "avatar_url": character.avatar_url,
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting current character: {e}")
            return None
    
    async def switch_character(self, character_id: int, character_name: str) -> bool:
        """Switch to a different character"""
        try:
            character = await db_ops.get_character(character_id)
            if character:
                self._current_character_id = character_id
                
                # Emit character switch event
                await self._event_system.emit(
                    EventType.CHAT_RESPONSE,
                    f"Switched to character: {character_name}",
                    {
                        "character_id": character_id,
                        "character_name": character_name,
                        "action": "character_switch"
                    }
                )
                
                logger.info(f"Switched to character: {character_name}")
                return True
            
            logger.error(f"Character not found: {character_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error switching character: {e}")
            return False
    
    async def process_message(self, message: str, character_id: int, character_name: str, user_id: Optional[str] = None) -> ChatResponse:
        """Process a chat message and generate AI response with memory"""
        try:
            # Get character details
            character = await db_ops.get_character(character_id)
            if not character:
                raise ValueError(f"Character not found: {character_id}")
            
            # Use provided user_id or default
            user_id = user_id or self._current_user_id
            
            # Lazy load LLM service
            if self._llm_service is None:
                try:
                    from ..llm import LLMService
                    self._llm_service = LLMService()
                except ImportError as e:
                    logger.error(f"Failed to import LLMService: {e}")
                    raise RuntimeError(f"LLM service is required but not available: {e}")
            
            # Generate response using unified LLM service with memory
            llm_response = await self._llm_service.generate_response(
                message=message,
                session_id=self._current_session_id or "temp_session",
                user_id=user_id,
                character_id=character.id,
                character_name=character.name,
                character_personality=character.personality,
                character_profile=character.profile
            )
            
            # Update current session ID
            if "session_id" in llm_response:
                self._current_session_id = llm_response["session_id"]
            
            # Convert dictionary response to ChatResponse object
            response = ChatResponse(
                user_input=message,
                response=llm_response["response"],
                character=character_name,
                emotion=llm_response.get("emotion", "neutral"),
                model_used=llm_response.get("model_used", "unknown")
            )
            
            # Add session info to response metadata
            if hasattr(response, 'metadata'):
                response.metadata = {
                    "session_id": llm_response.get("session_id"),
                    "turn_number": llm_response.get("turn_number")
                }
            
            logger.info(f"Generated response for {character_name}: {len(response.response)} chars (Turn {llm_response.get('turn_number', 0)})")
            return response
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise RuntimeError(f"Failed to process message: {e}")
    
    async def generate_tts(self, text: str, character_id: int, character_name: str) -> Optional[Path]:
        """Generate TTS audio for given text"""
        try:
            # Lazy load TTS service
            if self._tts_service is None:
                try:
                    from ..voice.tts.chatterbox_tts_service import ChatterboxTTSService
                    self._tts_service = ChatterboxTTSService()
                except ImportError as e:
                    logger.error(f"Failed to import ChatterboxTTSService: {e}")
                    raise RuntimeError(f"ChatterboxTTSService is required but not available: {e}")
            
            # Generate TTS audio
            try:
                audio_path = await self._tts_service.generate_speech(
                    text=text,
                    character_name=character_name,
                    voice=None
                )
                
                if audio_path and audio_path.exists():
                    logger.info(f"Generated TTS audio: {audio_path}")
                    return audio_path
                else:
                    logger.error(f"TTS generation failed - no audio file produced")
                    return None
                    
            except Exception as e:
                logger.error(f"Piper TTS service failed: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            return None
    
    async def get_conversation_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get conversation summary for current or specified session"""
        try:
            if self._llm_service is None:
                from ..llm import LLMService
                self._llm_service = LLMService()
            
            target_session = session_id or self._current_session_id
            if not target_session:
                return {"error": "No active conversation session"}
            
            return await self._llm_service.get_conversation_summary(target_session)
            
        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return {"error": str(e)}
    
    async def search_conversation_history(self, query: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search through conversation history"""
        try:
            if self._llm_service is None:
                from ..llm import LLMService
                self._llm_service = LLMService()
            
            target_session = session_id or self._current_session_id
            results = await self._llm_service.search_conversation_history(query, target_session)
            
            # Convert to dict format for API response
            return [
                {
                    "turn_id": result.turn_id,
                    "session_id": result.session_id,
                    "speaker": result.speaker_id,
                    "message": result.message,
                    "timestamp": result.timestamp.isoformat(),
                    "importance_score": result.importance_score
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error searching conversation history: {e}")
            return []
    
    def set_user_id(self, user_id: str):
        """Set the current user ID for session tracking"""
        self._current_user_id = user_id
        logger.info(f"Set user ID: {user_id}")
    
    def get_current_session_id(self) -> Optional[str]:
        """Get the current session ID"""
        return self._current_session_id
    
    def __str__(self) -> str:
        """String representation"""
        current_char = "None"
        if self._current_character_id:
            current_char = f"ID:{self._current_character_id}"
        
        return f"ChatService(current_character={current_char})"
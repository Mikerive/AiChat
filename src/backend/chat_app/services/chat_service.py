"""
Chat service for handling character conversations
"""

import logging
import sys
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants.paths import AUDIO_OUTPUT, ensure_dirs
 
from database import db_ops, Character
from event_system import get_event_system, EventType, EventSeverity

logger = logging.getLogger(__name__)


class ChatResponse:
    """Chat response data structure"""
    
    def __init__(self, response: str, emotion: Optional[str] = None, model_used: Optional[str] = None):
        self.response = response
        self.emotion = emotion
        self.model_used = model_used


class ChatService:
    """Service for handling character chat functionality"""
    
    def __init__(self):
        self.current_character: Optional[Dict[str, Any]] = None
        self.event_system = get_event_system()
        self._initialized = False
        # Don't initialize character during construction - do it lazily when first needed
    
    async def _ensure_initialized(self):
        """Ensure the service is initialized with a default character"""
        if not self._initialized:
            await self._initialize_default_character()
    
    async def _initialize_default_character(self):
        """Initialize with default character (async)"""
        if self._initialized:
            return
            
        try:
            # Try to get default character (await async db call)
            character = await db_ops.get_character_by_name("hatsune_miku")
            if character:
                self.current_character = {
                    "id": character.id,
                    "name": character.name,
                    "profile": character.profile,
                    "personality": character.personality
                }
            else:
                # Create default character
                character = await db_ops.create_character(
                    name="hatsune_miku",
                    profile="hatsune_miku",
                    personality="cheerful,curious,helpful"
                )
                if character:
                    self.current_character = {
                        "id": character.id,
                        "name": character.name,
                        "profile": character.profile,
                        "personality": character.personality
                    }
            
            self._initialized = True
            logger.info("Default character initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing default character: {e}", exc_info=True)
            # Set initialized anyway to avoid repeated attempts
            self._initialized = True
    
    async def process_message(self, message: str, character_id: int, character_name: str) -> ChatResponse:
        """Process a chat message and generate response"""
        await self._ensure_initialized()
        try:
            # Get character
            character = await db_ops.get_character(character_id)
            if not character:
                raise ValueError(f"Character not found: {character_id}")
            
            # Generate response (placeholder implementation)
            response = await self._generate_response(message, character)
            
            # Emit chat event
            await self.event_system.emit(
                EventType.CHAT_RESPONSE,
                f"Response from {character.name}",
                {
                    "character_id": character_id,
                    "character_name": character_name,
                    "user_message": message,
                    "response": response.response,
                    "emotion": response.emotion
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.event_system.emit(
                EventType.ERROR_OCCURRED,
                f"Chat processing error: {e}",
                {"message": message, "character_id": character_id},
                EventSeverity.ERROR
            )
            raise
    
    async def _generate_response(self, message: str, character: Character) -> ChatResponse:
        """Generate character response using OpenRouter LLM"""
        try:
            from .openrouter_service import OpenRouterService
            
            # Use OpenRouter service for LLM processing
            openrouter_service = OpenRouterService()
            
            try:
                result = await openrouter_service.generate_response(
                    message=message,
                    character_name=character.name,
                    character_personality=character.personality,
                    character_profile=character.profile
                )
                
                return ChatResponse(
                    response=result["response"],
                    emotion=result["emotion"],
                    model_used=result["model_used"]
                )
                
            finally:
                await openrouter_service.close()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            
            # Fallback to simple response generation
            try:
                personality_traits = character.personality.split(',') if character.personality else ["friendly"]
                
                # Basic response patterns
                responses = {
                    "cheerful": [
                        f"That's wonderful! I'm so glad to hear that!",
                        f"Yay! That sounds amazing!",
                        f"Awesome! I love hearing good news!"
                    ],
                    "curious": [
                        f"That's interesting! Tell me more about that.",
                        f"I'd love to learn more! What do you think?",
                        f"Fascinating! Can you explain more?"
                    ],
                    "helpful": [
                        f"I'm here to help! How can I assist you?",
                        f"Let me help you. What would you like to know?",
                        f"I'd be happy to help you. What do you need?"
                    ]
                }
                
                # Select response based on personality
                response_text = "I'm not sure how to respond to that, but I'm happy to chat with you!"
                for trait in personality_traits:
                    trait = trait.strip().lower()
                    if trait in responses:
                        response_text = responses[trait][0]
                        break
                
                # Add character-specific greeting
                if character.name.lower() == "hatsune_miku":
                    response_text = f"Hello! I'm Hatsune Miku! {response_text}"
                
                return ChatResponse(
                    response=response_text,
                    emotion="neutral",
                    model_used="fallback_local"
                )
                
            except Exception as fallback_error:
                logger.error(f"Error in fallback response generation: {fallback_error}")
                return ChatResponse(
                    response="I'm having trouble responding right now. Please try again later.",
                    emotion="confused",
                    model_used="error"
                )
    
    async def switch_character(self, character_id: int, character_name: str) -> None:
        """Switch to a different character"""
        try:
            character = await db_ops.get_character(character_id)
            if not character:
                raise ValueError(f"Character not found: {character_id}")
            
            self.current_character = {
                "id": character.id,
                "name": character.name,
                "profile": character.profile,
                "personality": character.personality
            }
            
            logger.info(f"Switched to character: {character.name}")
            
        except Exception as e:
            logger.error(f"Error switching character: {e}")
            raise
    
    async def get_current_character(self) -> Optional[Dict[str, Any]]:
        """Get current character"""
        return self.current_character
    
    async def list_characters(self) -> list:
        """List all available characters"""
        try:
            characters = await db_ops.list_characters()
            return [
                {
                    "id": char.id,
                    "name": char.name,
                    "profile": char.profile,
                    "personality": char.personality
                } for char in characters
            ]
        except Exception as e:
            logger.error(f"Error listing characters: {e}")
            return []
    
    async def get_character_history(self, character_id: int, limit: int = 50) -> list:
        """Get chat history for a character"""
        try:
            chat_logs = await db_ops.get_chat_logs(character_id=character_id, limit=limit)
            return [
                {
                    "id": log.id,
                    "user_message": log.user_message,
                    "character_response": log.character_response,
                    "timestamp": log.timestamp.isoformat(),
                    "emotion": log.emotion,
                    "metadata": log.metadata
                } for log in chat_logs
            ]
        except Exception as e:
            logger.error(f"Error getting character history: {e}")
            return []
    
    async def generate_tts(self, text: str, character_id: int, character_name: str) -> Optional[Path]:
        """Generate text-to-speech audio using Piper TTS"""
        try:
            from .piper_tts_service import PiperTTSService
            
            # Use Piper TTS service for audio generation
            piper_service = PiperTTSService()
            
            # Generate speech audio
            audio_path = await piper_service.generate_speech(
                text=text,
                character_name=character_name
            )
            
            if audio_path:
                logger.info(f"Generated TTS audio: {audio_path}")
                return audio_path
            else:
                logger.error("TTS generation returned no audio file")
                return None
            
        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            
            # Fallback: create a simple placeholder file
            try:
                audio_dir = AUDIO_OUTPUT
                ensure_dirs(audio_dir)
                
                import hashlib
                text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                audio_path = audio_dir / f"{character_name}_{text_hash}_fallback.wav"
                
                # Create minimal WAV file
                wav_header = bytes([
                    0x52, 0x49, 0x46, 0x46,  # "RIFF"
                    0x2C, 0xAC, 0x00, 0x00,  # File size
                    0x57, 0x41, 0x56, 0x45,  # "WAVE"
                    0x66, 0x6D, 0x74, 0x20,  # "fmt "
                    0x10, 0x00, 0x00, 0x00,  # Subchunk1Size
                    0x01, 0x00,              # AudioFormat (PCM)
                    0x01, 0x00,              # NumChannels (1)
                    0x22, 0x56, 0x00, 0x00,  # SampleRate (22050)
                    0x44, 0xAC, 0x00, 0x00,  # ByteRate
                    0x02, 0x00,              # BlockAlign
                    0x10, 0x00,              # BitsPerSample
                    0x64, 0x61, 0x74, 0x61,  # "data"
                    0x00, 0xAC, 0x00, 0x00   # Subchunk2Size
                ])
                
                with open(audio_path, 'wb') as f:
                    f.write(wav_header)
                    f.write(b'\x00' * 44100)  # 1 second of silence
                
                logger.info(f"Created fallback TTS audio: {audio_path}")
                return audio_path
                
            except Exception as fallback_error:
                logger.error(f"Error creating fallback TTS: {fallback_error}")
                return None
    
    async def get_chat_status(self) -> Dict[str, Any]:
        """Get chat system status"""
        try:
            return {
                "status": "active",
                "current_character": self.current_character,
                "characters_count": len(await self.list_characters()),
                "services": {
                    "chat": "ready",
                    "tts": "ready",
                    "llm": "ready"
                }
            }
        except Exception as e:
            logger.error(f"Error getting chat status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
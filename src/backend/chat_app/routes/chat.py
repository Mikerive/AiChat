"""
Chat API endpoints for VTuber backend
"""

import logging
import sys
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from database import db_ops, Character, ChatLog
from event_system import get_event_system, EventType, EventSeverity, emit_chat_response
from backend.chat_app.services.chat_service import ChatService
from backend.chat_app.services.whisper_service import WhisperService
from backend.chat_app.models.schemas import (
    CharacterResponse, ChatMessage, CharacterSwitch,
    TTSRequest, Character as CharacterSchema
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatServiceDep:
    """Chat service dependency"""
    
    def __init__(self):
        self.chat_service = ChatService()
        self.whisper_service = WhisperService()
    
    async def get_chat_service(self) -> ChatService:
        return self.chat_service
    
    async def get_whisper_service(self) -> WhisperService:
        return self.whisper_service


@router.get("/characters", response_model=List[CharacterSchema])
async def list_characters(chat_service: ChatService = Depends(ChatServiceDep().get_chat_service)):
    """List all available characters"""
    try:
        characters = await db_ops.list_characters()
        return [
            CharacterSchema(
                id=char.id,
                name=char.name,
                profile=char.profile,
                personality=char.personality,
                avatar_url=char.avatar_url
            ) for char in characters
        ]
    except Exception as e:
        logger.error(f"Error listing characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/characters/{character_id}", response_model=CharacterSchema)
async def get_character(
    character_id: int,
    chat_service: ChatService = Depends(ChatServiceDep().get_chat_service)
):
    """Get character by ID"""
    try:
        character = await db_ops.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        return CharacterSchema(
            id=character.id,
            name=character.name,
            profile=character.profile,
            personality=character.personality,
            avatar_url=character.avatar_url
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting character {character_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=CharacterResponse)
async def chat_with_character(
    message: ChatMessage,
    chat_service: ChatService = Depends(ChatServiceDep().get_chat_service)
):
    """Send chat message to character"""
    try:
        # Get character
        character = await db_ops.get_character_by_name(message.character)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Process chat message
        response = await chat_service.process_message(
            message.text,
            character.id,
            message.character
        )
        
        # Save to database
        await db_ops.create_chat_log(
            character_id=character.id,
            user_message=message.text,
            character_response=response.response,
            emotion=response.emotion,
            metadata={"model_used": response.model_used}
        )
        
        # Emit chat response event
        await emit_chat_response(
            f"Response from {character.name}",
            {
                "character": character.name,
                "response": response.response,
                "emotion": response.emotion,
                "model_used": response.model_used
            }
        )
        
        return CharacterResponse(
            user_input=message.text,
            character=message.character,
            character_name=character.name,
            response=response.response,
            emotion=response.emotion,
            model_used=response.model_used
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch_character")
async def switch_character(
    request: CharacterSwitch,
    chat_service: ChatService = Depends(ChatServiceDep().get_chat_service)
):
    """Switch active character"""
    try:
        # Get character
        character = await db_ops.get_character_by_name(request.character)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Switch character in service
        await chat_service.switch_character(character.id, request.character)
        
        # Emit character switch event
        from event_system import get_event_system
        event_system = get_event_system()
        await event_system.emit(
            EventType.CHARACTER_SWITCHED,
            f"Switched to {request.character}",
            {"character_id": character.id, "character_name": request.character}
        )
        
        return {
            "character": request.character,
            "character_name": character.name,
            "greeting": f"Switched to {request.character}",
            "status": "switched"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Character switch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts")
async def text_to_speech(
    request: TTSRequest,
    chat_service: ChatService = Depends(ChatServiceDep().get_chat_service)
):
    """Generate text-to-speech audio"""
    try:
        # Get character
        character = await db_ops.get_character_by_name(request.character)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Generate TTS audio
        audio_path = await chat_service.generate_tts(
            request.text,
            character.id,
            request.character
        )
        
        return {
            "text": request.text,
            "character": request.character,
            "character_name": character.name,
            "audio_file": str(audio_path) if audio_path else None,
            "audio_format": "wav",
            "status": "generated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stt")
async def speech_to_text(
    file: UploadFile = File(...),
    whisper_service: WhisperService = Depends(ChatServiceDep().get_whisper_service)
):
    """Convert speech to text using Whisper"""
    try:
        # Save uploaded file
        temp_file = Path("temp_audio") / file.filename
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_file, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Transcribe using Whisper
        result = await whisper_service.transcribe_audio(temp_file)
        
        # Clean up temp file
        temp_file.unlink()
        
        return {
            "text": result["text"],
            "language": result["language"],
            "confidence": result["confidence"],
            "processing_time": result["processing_time"]
        }
        
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history")
async def get_chat_history(
    character_id: Optional[int] = None,
    limit: int = 100,
    chat_service: ChatService = Depends(ChatServiceDep().get_chat_service)
):
    """Get chat history"""
    try:
        chat_logs = await db_ops.get_chat_logs(character_id=character_id, limit=limit)
        return {
            "history": [
                {
                    "id": log.id,
                    "character_id": log.character_id,
                    "user_message": log.user_message,
                    "character_response": log.character_response,
                    "timestamp": log.timestamp.isoformat(),
                    "emotion": log.emotion,
                    "metadata": log.metadata
                } for log in chat_logs
            ]
        }
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_chat_status(
    chat_service: ChatService = Depends(ChatServiceDep().get_chat_service)
):
    """Get chat system status"""
    try:
        current_character = await chat_service.get_current_character()
        
        return {
            "backend": "running",
            "chat_service": "active",
            "current_character": {
                "id": current_character["id"] if current_character else None,
                "name": current_character["name"] if current_character else None
            },
            "models": {
                "whisper": "loaded",
                "tts": "ready"
            }
        }
    except Exception as e:
        logger.error(f"Error getting chat status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
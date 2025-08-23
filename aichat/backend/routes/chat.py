"""
Chat API endpoints for VTuber backend
"""

import logging
from typing import List, Optional
from pathlib import Path

# Third-party imports
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

# Local imports
from aichat.models.schemas import Character as CharacterSchema
from aichat.models.schemas import (
    CharacterResponse,
    CharacterSwitch,
    CharacterSwitchResponse,
    ChatMessage,
    ChatHistoryResponse,
    SystemStatusResponse,
    TTSRequest,
    TTSResponse,
    STTResponse,
)
from aichat.backend.services.di_container import (
    get_chat_service,
    get_whisper_service, 
    get_chatterbox_tts_service,
)
from aichat.core.database import db_ops
from aichat.core.event_system import EventType, emit_chat_response, get_event_system

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency injection functions
def get_chat_service_dep():
    """Dependency injection for chat service"""
    return get_chat_service()


def get_whisper_service_dep():
    """Dependency injection for whisper service"""
    return get_whisper_service()


def get_chatterbox_tts_service_dep():
    """Dependency injection for ChatterboxTTS service"""
    return get_chatterbox_tts_service()


@router.get("/characters", response_model=List[CharacterSchema])
async def list_characters(chat_service=Depends(get_chat_service_dep)):
    """List all available characters"""
    try:
        characters = await db_ops.list_characters()
        return [
            CharacterSchema(
                id=char.id,
                name=char.name,
                profile=char.profile,
                personality=char.personality,
                avatar_url=char.avatar_url,
            )
            for char in characters
        ]
    except Exception as e:
        logger.error(f"Error listing characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/characters/{character_id}", response_model=CharacterSchema)
async def get_character(character_id: int, chat_service=Depends(get_chat_service_dep)):
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
            avatar_url=character.avatar_url,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting character {character_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=CharacterResponse)
async def chat_with_character(
    message: ChatMessage, chat_service=Depends(get_chat_service_dep)
):
    """Send chat message to character"""
    try:
        # Get character
        character = await db_ops.get_character_by_name(message.character)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Process chat message
        response = await chat_service.process_message(
            message.text, character.id, message.character
        )

        # Save to database
        await db_ops.create_chat_log(
            character_id=character.id,
            user_message=message.text,
            character_response=response.response,
            emotion=response.emotion,
            metadata={"model_used": response.model_used},
        )

        # Emit chat response event
        await emit_chat_response(
            f"Response from {character.name}",
            {
                "character": character.name,
                "response": response.response,
                "emotion": response.emotion,
                "model_used": response.model_used,
            },
        )

        return CharacterResponse(
            user_input=message.text,
            character=message.character,
            character_name=character.name,
            response=response.response,
            emotion=response.emotion,
            model_used=response.model_used,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch_character", response_model=CharacterSwitchResponse)
async def switch_character(
    request: CharacterSwitch, chat_service=Depends(get_chat_service_dep)
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

        event_system = get_event_system()
        await event_system.emit(
            EventType.CHARACTER_SWITCHED,
            f"Switched to {request.character}",
            {"character_id": character.id, "character_name": request.character},
        )

        return CharacterSwitchResponse(
            character=request.character,
            character_name=character.name,
            greeting=f"Switched to {request.character}",
            status="switched"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Character switch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(
    request: TTSRequest, tts_service=Depends(get_chatterbox_tts_service_dep)
):
    """Generate text-to-speech audio using ChatterboxTTS with improved segmentation"""
    try:
        # Get character
        character = await db_ops.get_character_by_name(request.character)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Generate TTS audio using ChatterboxTTS directly
        audio_path = await tts_service.generate_speech(
            text=request.text,
            character_name=request.character,
            voice=None,  # Use default voice
            exaggeration=0.8  # Slightly more expressive
        )

        return TTSResponse(
            audio_file=str(audio_path) if audio_path else "",
            audio_format="wav",
            character=request.character,
            text=request.text
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts/streaming")
async def text_to_speech_streaming(
    request: TTSRequest, tts_service=Depends(get_chatterbox_tts_service_dep)
):
    """Generate streaming text-to-speech audio with sentence-based segmentation"""
    try:
        # Get character
        character = await db_ops.get_character_by_name(request.character)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Generate streaming TTS segments
        segments = await tts_service.generate_streaming_speech(
            text=request.text,
            character_name=request.character,
            voice=None,
            exaggeration=0.8
        )

        return {
            "status": "success",
            "character": request.character,
            "text": request.text,
            "segments": segments,
            "total_segments": len(segments)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Streaming TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    file: UploadFile = File(...), whisper_service=Depends(get_whisper_service_dep)
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

        return STTResponse(
            text=result["text"],
            language=result["language"],
            confidence=result["confidence"],
            processing_time=result.get("processing_time", 0.0)
        )

    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    character_id: Optional[int] = None,
    limit: int = 100,
    chat_service=Depends(get_chat_service_dep),
):
    """Get chat history"""
    try:
        chat_logs = await db_ops.get_chat_logs(character_id=character_id, limit=limit)
        return ChatHistoryResponse(
            history=[
                {
                    "id": log.id,
                    "character_id": log.character_id,
                    "user_message": log.user_message,
                    "character_response": log.character_response,
                    "timestamp": log.timestamp.isoformat(),
                    "emotion": log.emotion,
                    "metadata": log.metadata,
                }
                for log in chat_logs
            ]
        )
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=SystemStatusResponse)
async def get_chat_status(chat_service=Depends(get_chat_service_dep)):
    """Get chat system status"""
    try:
        current_character = await chat_service.get_current_character()

        return SystemStatusResponse(
            backend="running",
            chat_service="active",
            current_character={
                "id": str(current_character["id"]) if current_character and current_character.get("id") else None,
                "name": current_character["name"] if current_character else None,
            },
            models={"whisper": "loaded", "tts": "ready"}
        )
    except Exception as e:
        logger.error(f"Error getting chat status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

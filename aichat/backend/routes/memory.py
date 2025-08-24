"""
Memory management API endpoints
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

# Local imports
from aichat.backend.services.llm.memory import MemoryManager
from aichat.backend.services.di_container import get_chat_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Request/Response models
class SessionRequest(BaseModel):
    user_id: str
    character_id: int
    character_name: str

class SessionResponse(BaseModel):
    session_id: str
    character_id: int
    character_name: str
    started_at: str
    participants: List[str]
    total_turns: int
    compression_count: int

class ConversationSummaryResponse(BaseModel):
    session_id: str
    character: str
    participants: List[str]
    total_turns: int
    compression_count: int
    summary: str
    key_topics: List[tuple]
    emotional_journey: str
    important_facts: List[str]

class SearchRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    limit: int = 10

class SearchResult(BaseModel):
    turn_id: int
    session_id: str
    speaker: str
    message: str
    timestamp: str
    importance_score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_found: int

# Dependency injection
def get_memory_manager():
    """Get memory manager instance"""
    return MemoryManager()

def get_chat_service_dep():
    """Get chat service instance"""
    return get_chat_service()


@router.post("/sessions/start", response_model=SessionResponse)
async def start_session(
    request: SessionRequest,
    memory_manager: MemoryManager = Depends(get_memory_manager)
):
    """Start a new conversation session"""
    try:
        session = await memory_manager.start_session(
            character_id=request.character_id,
            character_name=request.character_name,
            user_id=request.user_id
        )
        
        return SessionResponse(
            session_id=session.session_id,
            character_id=session.character_id,
            character_name=session.character_name,
            started_at=session.started_at.isoformat(),
            participants=session.participants,
            total_turns=session.total_turns,
            compression_count=session.compression_count
        )
        
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/summary", response_model=ConversationSummaryResponse)
async def get_session_summary(
    session_id: str,
    chat_service=Depends(get_chat_service_dep)
):
    """Get summary of a conversation session"""
    try:
        summary = await chat_service.get_conversation_summary(session_id)
        
        if "error" in summary:
            raise HTTPException(status_code=404, detail=summary["error"])
            
        return ConversationSummaryResponse(**summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/context")
async def get_session_context(
    session_id: str,
    memory_manager: MemoryManager = Depends(get_memory_manager)
):
    """Get current compressed context for a session"""
    try:
        context = await memory_manager.get_session_context(session_id)
        
        return {
            "session_id": session_id,
            "character_reminder": context.character_reminder,
            "session_summary": context.session_summary,
            "key_topics": context.key_topics,
            "emotional_journey": context.emotional_journey,
            "important_facts": context.important_facts,
            "preserved_turns": len(context.preserved_turns),
            "recent_turns": len(context.recent_turns),
            "estimated_tokens": context.get_token_count(),
            "compression_metadata": context.compression_metadata
        }
        
    except Exception as e:
        logger.error(f"Error getting session context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/compress")
async def force_compression(
    session_id: str,
    memory_manager: MemoryManager = Depends(get_memory_manager)
):
    """Force compression of a conversation session"""
    try:
        compressed = await memory_manager.compress_conversation(session_id)
        
        return {
            "session_id": session_id,
            "compression_successful": True,
            "tokens_saved": compressed.compression_metadata.get("tokens_saved", 0),
            "preserved_turns": len(compressed.preserved_turns),
            "compression_number": compressed.compression_metadata.get("compression_number", 0)
        }
        
    except Exception as e:
        logger.error(f"Error compressing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    limit: Optional[int] = Query(None, description="Limit number of turns returned"),
    memory_manager: MemoryManager = Depends(get_memory_manager)
):
    """Get full conversation history for a session"""
    try:
        history = await memory_manager.get_session_history(session_id, limit)
        
        return {
            "session_id": session_id,
            "total_turns": len(history),
            "history": [
                {
                    "turn_id": turn.turn_id,
                    "speaker_id": turn.speaker_id,
                    "speaker_type": turn.speaker_type,
                    "message": turn.message,
                    "timestamp": turn.timestamp.isoformat(),
                    "metadata": turn.metadata
                }
                for turn in history
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_memories(
    request: SearchRequest,
    chat_service=Depends(get_chat_service_dep)
):
    """Search through conversation memories"""
    try:
        results = await chat_service.search_conversation_history(
            query=request.query,
            session_id=request.session_id
        )
        
        # Limit results
        limited_results = results[:request.limit]
        
        search_results = [
            SearchResult(
                turn_id=result["turn_id"],
                session_id=result["session_id"],
                speaker=result["speaker"],
                message=result["message"],
                timestamp=result["timestamp"],
                importance_score=result["importance_score"]
            )
            for result in limited_results
        ]
        
        return SearchResponse(
            results=search_results,
            total_found=len(results)
        )
        
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_active_sessions(
    memory_manager: MemoryManager = Depends(get_memory_manager)
):
    """List all active conversation sessions"""
    try:
        # This would need to be implemented in MemoryManager
        # For now, return placeholder
        return {
            "active_sessions": [],
            "message": "Session listing not yet implemented"
        }
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def close_session(
    session_id: str,
    memory_manager: MemoryManager = Depends(get_memory_manager)
):
    """Close and archive a conversation session"""
    try:
        # Close session via session manager
        session_manager = memory_manager.session_manager
        await session_manager.close_session(session_id)
        
        return {
            "session_id": session_id,
            "status": "closed"
        }
        
    except Exception as e:
        logger.error(f"Error closing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_memory_stats(
    memory_manager: MemoryManager = Depends(get_memory_manager)
):
    """Get memory system statistics"""
    try:
        # This would need implementation in MemoryManager
        return {
            "total_sessions": 0,
            "active_sessions": 0,
            "total_turns": 0,
            "total_compressions": 0,
            "message": "Stats not yet implemented"
        }
        
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
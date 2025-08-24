"""
Session management for conversation memory system
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from uuid import uuid4

from .models import ConversationSession, ConversationTurn
from aichat.core.database import db_ops
from aichat.core.event_system import EventType, get_event_system

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages conversation sessions and their lifecycle"""
    
    def __init__(self):
        self.event_system = get_event_system()
        self._active_sessions: Dict[str, ConversationSession] = {}
        self._session_timeout_hours = 24  # Sessions expire after 24 hours of inactivity
        
    async def create_session(
        self,
        character_id: int,
        character_name: str,
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> ConversationSession:
        """Create a new conversation session"""
        
        session = ConversationSession(
            session_id=str(uuid4()),
            character_id=character_id,
            character_name=character_name,
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            participants=[user_id],
            metadata=metadata or {}
        )
        
        # Store in memory cache
        self._active_sessions[session.session_id] = session
        
        # Store in database
        await self._persist_session(session)
        
        # Emit event
        await self.event_system.emit(
            EventType.SYSTEM_STATUS,
            f"New conversation session started with {character_name}",
            {
                "session_id": session.session_id,
                "character_id": character_id,
                "user_id": user_id
            }
        )
        
        logger.info(f"Created session {session.session_id} for character {character_name}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get an existing session by ID"""
        
        # Check memory cache first
        if session_id in self._active_sessions:
            session = self._active_sessions[session_id]
            
            # Check if session expired
            if self._is_session_expired(session):
                await self.close_session(session_id)
                return None
                
            return session
        
        # Try to load from database
        session = await self._load_session_from_db(session_id)
        if session and not self._is_session_expired(session):
            self._active_sessions[session_id] = session
            return session
            
        return None
    
    async def get_or_create_session(
        self,
        user_id: str,
        character_id: int,
        character_name: str
    ) -> ConversationSession:
        """Get existing session or create new one"""
        
        # Check for recent session with same user and character
        for session_id, session in self._active_sessions.items():
            if (session.character_id == character_id and 
                user_id in session.participants and
                not self._is_session_expired(session)):
                
                logger.info(f"Reusing existing session {session_id}")
                return session
        
        # Create new session
        return await self.create_session(character_id, character_name, user_id)
    
    async def add_participant(self, session_id: str, user_id: str) -> bool:
        """Add a participant to an existing session"""
        
        session = await self.get_session(session_id)
        if not session:
            return False
            
        if user_id not in session.participants:
            session.participants.append(user_id)
            await self._persist_session(session)
            
            logger.info(f"Added participant {user_id} to session {session_id}")
            
        return True
    
    async def update_session_activity(self, session_id: str, turn_count: int = 0, token_count: int = 0):
        """Update session activity and stats"""
        
        session = await self.get_session(session_id)
        if not session:
            return
            
        session.update_activity()
        session.total_turns += turn_count
        session.total_tokens += token_count
        
        # Persist periodically (every 10 turns)
        if session.total_turns % 10 == 0:
            await self._persist_session(session)
    
    async def record_compression(self, session_id: str):
        """Record that a compression occurred"""
        
        session = await self.get_session(session_id)
        if session:
            session.compression_count += 1
            await self._persist_session(session)
    
    async def close_session(self, session_id: str):
        """Close and archive a session"""
        
        if session_id in self._active_sessions:
            session = self._active_sessions[session_id]
            
            # Final persist
            await self._persist_session(session)
            
            # Remove from active cache
            del self._active_sessions[session_id]
            
            # Emit event
            await self.event_system.emit(
                EventType.SYSTEM_STATUS,
                f"Conversation session closed",
                {
                    "session_id": session_id,
                    "duration_minutes": int((datetime.utcnow() - session.started_at).total_seconds() / 60),
                    "total_turns": session.total_turns,
                    "compression_count": session.compression_count
                }
            )
            
            logger.info(f"Closed session {session_id}")
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions from memory"""
        
        expired = []
        for session_id, session in self._active_sessions.items():
            if self._is_session_expired(session):
                expired.append(session_id)
        
        for session_id in expired:
            await self.close_session(session_id)
            
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
    
    def _is_session_expired(self, session: ConversationSession) -> bool:
        """Check if a session has expired"""
        
        expiry_time = session.last_activity + timedelta(hours=self._session_timeout_hours)
        return datetime.utcnow() > expiry_time
    
    async def _persist_session(self, session: ConversationSession):
        """Persist session to database"""
        
        try:
            # Store session data
            await db_ops.execute_query(
                """
                INSERT OR REPLACE INTO conversation_sessions 
                (session_id, character_id, started_at, last_activity, 
                 participants, total_turns, compression_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.character_id,
                    session.started_at.isoformat(),
                    session.last_activity.isoformat(),
                    str(session.participants),  # JSON string
                    session.total_turns,
                    session.compression_count,
                    str(session.metadata)  # JSON string
                )
            )
        except Exception as e:
            logger.error(f"Failed to persist session {session.session_id}: {e}")
    
    async def _load_session_from_db(self, session_id: str) -> Optional[ConversationSession]:
        """Load session from database"""
        
        try:
            result = await db_ops.fetch_one(
                """
                SELECT * FROM conversation_sessions WHERE session_id = ?
                """,
                (session_id,)
            )
            
            if result:
                import json
                
                return ConversationSession(
                    session_id=result["session_id"],
                    character_id=result["character_id"],
                    started_at=datetime.fromisoformat(result["started_at"]),
                    last_activity=datetime.fromisoformat(result["last_activity"]),
                    participants=json.loads(result["participants"]),
                    total_turns=result["total_turns"],
                    compression_count=result["compression_count"],
                    metadata=json.loads(result["metadata"])
                )
                
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            
        return None
    
    async def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session"""
        
        session = await self.get_session(session_id)
        if not session:
            return {}
            
        duration = datetime.utcnow() - session.started_at
        
        return {
            "session_id": session.session_id,
            "character": session.character_name,
            "participants": session.participants,
            "started_at": session.started_at.isoformat(),
            "duration_minutes": int(duration.total_seconds() / 60),
            "total_turns": session.total_turns,
            "total_tokens": session.total_tokens,
            "compression_count": session.compression_count,
            "is_active": not self._is_session_expired(session)
        }
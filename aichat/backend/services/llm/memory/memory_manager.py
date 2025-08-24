"""
Main memory manager that orchestrates the conversation memory system
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .models import (
    ConversationSession,
    ConversationTurn,
    ConversationSummary,
    CompressedContext
)
from .session_manager import SessionManager
from .compression_engine import CompressionEngine
from .buffer_zone_manager import BufferZoneCompressionManager
from aichat.core.database import db_ops
from aichat.core.event_system import EventType, get_event_system

logger = logging.getLogger(__name__)


class MemoryManager:
    """Central manager for conversation memory"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.compression_engine = CompressionEngine()
        self.buffer_zone_manager = BufferZoneCompressionManager()
        self.event_system = get_event_system()
        
        # In-memory cache for active conversations
        self._turn_cache: Dict[str, List[ConversationTurn]] = {}
        self._context_cache: Dict[str, CompressedContext] = {}
        
        # Initialize database tables
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables for memory system"""
        
        # This would normally be done in migrations
        # For now, we'll ensure tables exist
        try:
            import asyncio
            asyncio.create_task(self._create_tables())
        except Exception as e:
            logger.warning(f"Could not initialize database tables: {e}")
    
    async def _create_tables(self):
        """Create necessary database tables"""
        
        queries = [
            """
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                character_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                participants TEXT NOT NULL,
                total_turns INTEGER DEFAULT 0,
                compression_count INTEGER DEFAULT 0,
                metadata TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                speaker_id TEXT NOT NULL,
                speaker_type TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                token_count INTEGER,
                metadata TEXT,
                importance_score REAL DEFAULT 0.0,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id),
                UNIQUE(session_id, turn_number)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                summary_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                summary_type TEXT NOT NULL,
                content TEXT NOT NULL,
                turn_start INTEGER NOT NULL,
                turn_end INTEGER NOT NULL,
                participants TEXT NOT NULL,
                importance_score REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS compression_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                compressed_at_turn INTEGER NOT NULL,
                original_token_count INTEGER NOT NULL,
                compressed_token_count INTEGER NOT NULL,
                preserved_turns TEXT NOT NULL,
                summary TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id)
            )
            """
        ]
        
        for query in queries:
            try:
                await db_ops.execute_query(query)
            except Exception as e:
                logger.error(f"Failed to create table: {e}")
    
    async def start_session(
        self,
        character_id: int,
        character_name: str,
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> ConversationSession:
        """Start a new conversation session"""
        
        session = await self.session_manager.create_session(
            character_id, character_name, user_id, metadata
        )
        
        # Initialize caches
        self._turn_cache[session.session_id] = []
        self._context_cache[session.session_id] = CompressedContext()
        
        logger.info(f"Started memory session {session.session_id}")
        return session
    
    async def get_or_create_session(
        self,
        user_id: str,
        character_id: int,
        character_name: str
    ) -> ConversationSession:
        """Get existing session or create new one"""
        
        session = await self.session_manager.get_or_create_session(
            user_id, character_id, character_name
        )
        
        # Ensure caches are initialized
        if session.session_id not in self._turn_cache:
            # Load existing turns from database
            turns = await self._load_session_turns(session.session_id)
            self._turn_cache[session.session_id] = turns
            
            # Load or create context
            context = await self._load_or_create_context(session.session_id)
            self._context_cache[session.session_id] = context
        
        return session
    
    async def add_turn(
        self,
        session_id: str,
        speaker_id: str,
        speaker_type: str,
        message: str,
        metadata: Optional[Dict] = None
    ) -> ConversationTurn:
        """Add a turn to the conversation"""
        
        # Get session
        session = await self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Get current turns
        if session_id not in self._turn_cache:
            self._turn_cache[session_id] = []
        
        turns = self._turn_cache[session_id]
        
        # Create new turn
        turn = ConversationTurn(
            turn_id=len(turns) + 1,
            session_id=session_id,
            speaker_id=speaker_id,
            speaker_type=speaker_type,
            message=message,
            timestamp=datetime.utcnow(),
            token_count=len(message) // 4,  # Rough estimate
            metadata=metadata or {}
        )
        
        # Add to cache
        turns.append(turn)
        
        # Persist to database
        await self._persist_turn(turn)
        
        # Update session activity
        await self.session_manager.update_session_activity(
            session_id, 
            turn_count=1,
            token_count=turn.token_count
        )
        
        # Two-stage compression check
        await self._handle_two_stage_compression(session_id, session, turn)
        
        logger.debug(f"Added turn {turn.turn_id} to session {session_id}")
        return turn
    
    async def compress_conversation(self, session_id: str) -> CompressedContext:
        """Compress the conversation for a session"""
        
        # Get session and turns
        session = await self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        turns = self._turn_cache.get(session_id, [])
        if not turns:
            return CompressedContext()
        
        # Get character data
        character = await db_ops.get_character(session.character_id)
        character_data = {
            "name": character.name,
            "personality": character.personality,
            "profile": character.profile
        } if character else {}
        
        # Calculate current tokens
        current_tokens = sum(t.token_count for t in turns)
        
        # Compress conversation
        compressed = await self.compression_engine.compress(
            session, turns, character_data
        )
        
        # Update cache
        self._context_cache[session_id] = compressed
        
        # Clear old turns from cache, keep only recent
        keep_count = self.compression_engine.COMPRESSION_CONFIG["recent_turns_keep"]
        self._turn_cache[session_id] = turns[-keep_count:]
        
        # Update session
        await self.session_manager.record_compression(session_id)
        
        # Emit event
        await self.event_system.emit(
            EventType.SYSTEM_STATUS,
            f"Conversation compressed for session {session_id}",
            {
                "session_id": session_id,
                "original_turns": len(turns),
                "compressed_tokens": compressed.get_token_count(),
                "tokens_saved": compressed.compression_metadata.get("tokens_saved", 0)
            }
        )
        
        logger.info(f"Compressed conversation for session {session_id}")
        return compressed
    
    async def get_session_context(self, session_id: str) -> CompressedContext:
        """Get the current context for a session"""
        
        # Check cache first
        if session_id in self._context_cache:
            context = self._context_cache[session_id]
            
            # Add any new turns since compression
            if session_id in self._turn_cache:
                recent_turns = self._turn_cache[session_id]
                if recent_turns:
                    # Update recent turns in context
                    context.recent_turns = recent_turns[-10:]  # Last 10 turns
            
            return context
        
        # Load from database or create new
        return await self._load_or_create_context(session_id)
    
    async def search_memories(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[ConversationTurn]:
        """Search through conversation memories"""
        
        try:
            # Build search query
            if session_id:
                sql = """
                    SELECT * FROM conversation_turns 
                    WHERE session_id = ? AND message LIKE ?
                    ORDER BY importance_score DESC, turn_number DESC
                    LIMIT ?
                """
                params = (session_id, f"%{query}%", limit)
            else:
                sql = """
                    SELECT * FROM conversation_turns 
                    WHERE message LIKE ?
                    ORDER BY importance_score DESC, timestamp DESC
                    LIMIT ?
                """
                params = (f"%{query}%", limit)
            
            results = await db_ops.fetch_all(sql, params)
            
            # Convert to ConversationTurn objects
            turns = []
            for row in results:
                import json
                turn = ConversationTurn(
                    turn_id=row["turn_number"],
                    session_id=row["session_id"],
                    speaker_id=row["speaker_id"],
                    speaker_type=row["speaker_type"],
                    message=row["message"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    token_count=row["token_count"] or 0,
                    metadata=json.loads(row["metadata"] or "{}"),
                    importance_score=row["importance_score"] or 0.0
                )
                turns.append(turn)
            
            return turns
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def get_session_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationTurn]:
        """Get full conversation history for a session"""
        
        # Check cache first
        if session_id in self._turn_cache:
            turns = self._turn_cache[session_id]
            if limit:
                return turns[-limit:]
            return turns
        
        # Load from database
        return await self._load_session_turns(session_id, limit)
    
    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of a conversation session"""
        
        # Get session
        session = await self.session_manager.get_session(session_id)
        if not session:
            return {}
        
        # Get context
        context = await self.get_session_context(session_id)
        
        # Get stats
        stats = await self.session_manager.get_session_stats(session_id)
        
        # Build summary
        summary = {
            "session_id": session_id,
            "character": session.character_name,
            "participants": session.participants,
            "stats": stats,
            "summary": context.session_summary,
            "key_topics": context.key_topics,
            "emotional_journey": context.emotional_journey,
            "important_facts": context.important_facts,
            "compression_count": session.compression_count,
            "total_turns": session.total_turns
        }
        
        return summary
    
    async def _handle_two_stage_compression(
        self,
        session_id: str,
        session: ConversationSession,
        new_turn: ConversationTurn
    ):
        """Handle the two-stage compression workflow"""
        
        turns = self._turn_cache.get(session_id, [])
        if not turns:
            return
        
        # Check for 75% threshold (start background compression)
        if await self.buffer_zone_manager.should_trigger_compression(session_id, turns):
            logger.info(f"75% threshold reached for session {session_id}, starting background compression")
            
            # Get character data
            character = await db_ops.get_character(session.character_id)
            character_data = {
                "name": character.name,
                "personality": character.personality,
                "profile": character.profile
            } if character else {}
            
            # Start background compression
            await self.buffer_zone_manager.start_background_compression(
                session_id, session, turns, character_data
            )
        
        # Collect buffer zone turns (75%-85%)
        await self.buffer_zone_manager.collect_buffer_turn(session_id, new_turn)
        
        # Check for 85% threshold (immediate context reset)
        if await self.buffer_zone_manager.should_reset_context(session_id, turns):
            logger.info(f"85% threshold reached for session {session_id}, resetting context")
            
            # Package and reset context immediately
            new_context = await self.buffer_zone_manager.package_and_reset_context(session_id, turns)
            
            # Update context cache
            self._context_cache[session_id] = new_context
            
            # Keep only recent turns in cache
            keep_count = self.buffer_zone_manager.RECENT_TURNS_KEEP
            self._turn_cache[session_id] = turns[-keep_count:] if len(turns) > keep_count else turns
            
            # Update session compression count
            await self.session_manager.record_compression(session_id)
            
            logger.info(f"Context reset completed for session {session_id}")
    
    async def _persist_turn(self, turn: ConversationTurn):
        """Persist a turn to the database"""
        
        try:
            import json
            
            await db_ops.execute_query(
                """
                INSERT INTO conversation_turns 
                (session_id, turn_number, speaker_id, speaker_type, 
                 message, timestamp, token_count, metadata, importance_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn.session_id,
                    turn.turn_id,
                    turn.speaker_id,
                    turn.speaker_type,
                    turn.message,
                    turn.timestamp.isoformat(),
                    turn.token_count,
                    json.dumps(turn.metadata),
                    turn.importance_score
                )
            )
        except Exception as e:
            logger.error(f"Failed to persist turn: {e}")
    
    async def _load_session_turns(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationTurn]:
        """Load turns for a session from database"""
        
        try:
            sql = """
                SELECT * FROM conversation_turns 
                WHERE session_id = ?
                ORDER BY turn_number
            """
            
            if limit:
                sql += f" LIMIT {limit}"
            
            results = await db_ops.fetch_all(sql, (session_id,))
            
            turns = []
            for row in results:
                import json
                turn = ConversationTurn(
                    turn_id=row["turn_number"],
                    session_id=row["session_id"],
                    speaker_id=row["speaker_id"],
                    speaker_type=row["speaker_type"],
                    message=row["message"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    token_count=row["token_count"] or 0,
                    metadata=json.loads(row["metadata"] or "{}"),
                    importance_score=row["importance_score"] or 0.0
                )
                turns.append(turn)
            
            return turns
            
        except Exception as e:
            logger.error(f"Failed to load session turns: {e}")
            return []
    
    async def _load_or_create_context(self, session_id: str) -> CompressedContext:
        """Load existing context or create new one"""
        
        # For now, create empty context
        # In future, could reconstruct from compression events
        return CompressedContext()
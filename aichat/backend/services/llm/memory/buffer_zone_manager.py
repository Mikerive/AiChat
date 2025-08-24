"""
BufferZoneCompressionManager

Manages sophisticated two-stage compression with buffer zone context preservation.

Workflow:
1. Monitor token usage per session
2. At 75%: Start background compression (parallel, non-blocking)
3. 75%-85%: Collect buffer zone turns
4. At 85%: Package compressed + buffer + recent and reset context immediately
5. New context = compressed_summary + buffer_turns + recent_turns
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

from .models import ConversationSession, ConversationTurn, CompressedContext
from .compression_engine import CompressionEngine
from .summarization_model import SummarizationModel
from aichat.core.event_system import EventType, get_event_system

logger = logging.getLogger(__name__)


@dataclass
class CompressionState:
    """Tracks compression progress for a session"""
    session_id: str
    compression_started: bool = False
    compression_complete: bool = False
    started_at_turn: int = 0
    buffer_zone_turns: List[ConversationTurn] = field(default_factory=list)
    compressed_context: Optional[CompressedContext] = None
    compression_task: Optional[asyncio.Task] = None
    
    def __post_init__(self):
        """Ensure buffer_zone_turns is always a list"""
        if self.buffer_zone_turns is None:
            self.buffer_zone_turns = []


@dataclass
class CompressionStatus:
    """Status information for debugging/monitoring"""
    session_id: str
    token_percentage: float
    compression_triggered: bool
    compression_complete: bool
    buffer_zone_size: int
    ready_for_reset: bool
    tokens_saved: int = 0


class BufferZoneCompressionManager:
    """
    Manages two-stage compression with buffer zone context preservation
    
    Key Features:
    - 75% threshold triggers background compression (parallel)
    - 75%-85% buffer zone preserves conversation continuity
    - 85% threshold triggers immediate context reset
    - Intelligent packaging of compressed + buffer + recent context
    """
    
    def __init__(self):
        self.compression_engine = CompressionEngine()
        self.summarization_model = SummarizationModel()
        self.event_system = get_event_system()
        
        # Per-session state tracking
        self._compression_states: Dict[str, CompressionState] = {}
        
        # Configuration
        self.COMPRESSION_START_THRESHOLD = 0.75  # Start background compression
        self.CONTEXT_RESET_THRESHOLD = 0.85      # Immediate context reset
        self.MAX_CONTEXT_TOKENS = 8000           # Default model context limit
        self.RECENT_TURNS_KEEP = 10              # Recent turns after reset
    
    def _calculate_token_percentage(self, turns: List[ConversationTurn]) -> float:
        """Calculate current token usage as percentage of max context"""
        total_tokens = sum(turn.token_count for turn in turns)
        return total_tokens / self.MAX_CONTEXT_TOKENS if self.MAX_CONTEXT_TOKENS > 0 else 0.0
    
    def _get_or_create_state(self, session_id: str) -> CompressionState:
        """Get or create compression state for session"""
        if session_id not in self._compression_states:
            self._compression_states[session_id] = CompressionState(session_id=session_id)
        return self._compression_states[session_id]
    
    async def should_trigger_compression(
        self, 
        session_id: str, 
        turns: List[ConversationTurn]
    ) -> bool:
        """Check if 75% threshold reached and compression should start"""
        if not turns:
            return False
            
        state = self._get_or_create_state(session_id)
        
        # Don't trigger if already started
        if state.compression_started:
            return False
        
        percentage = self._calculate_token_percentage(turns)
        return percentage >= self.COMPRESSION_START_THRESHOLD
    
    async def should_reset_context(
        self, 
        session_id: str, 
        turns: List[ConversationTurn]
    ) -> bool:
        """Check if 85% threshold reached and context should reset"""
        if not turns:
            return False
            
        percentage = self._calculate_token_percentage(turns)
        return percentage >= self.CONTEXT_RESET_THRESHOLD
    
    async def start_background_compression(
        self,
        session_id: str,
        session: ConversationSession,
        turns: List[ConversationTurn],
        character_data: Dict[str, Any]
    ) -> bool:
        """Start parallel compression at 75% threshold"""
        try:
            state = self._get_or_create_state(session_id)
            
            if state.compression_started:
                logger.warning(f"Compression already started for session {session_id}")
                return False
            
            # Mark compression as started
            state.compression_started = True
            state.started_at_turn = len(turns)
            
            logger.info(f"Starting background compression for session {session_id} at turn {state.started_at_turn}")
            
            # Create background compression task
            state.compression_task = asyncio.create_task(
                self._background_compression_worker(session_id, session, turns, character_data)
            )
            
            # Emit event
            await self.event_system.emit(
                EventType.SYSTEM_STATUS,
                f"Background compression started for session {session_id}",
                {
                    "session_id": session_id,
                    "turn_count": len(turns),
                    "token_percentage": self._calculate_token_percentage(turns) * 100
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start background compression: {e}")
            return False
    
    async def _background_compression_worker(
        self,
        session_id: str,
        session: ConversationSession,
        turns: List[ConversationTurn],
        character_data: Dict[str, Any]
    ):
        """Background worker that performs the actual compression"""
        try:
            state = self._get_or_create_state(session_id)
            
            logger.info(f"Background compression worker started for session {session_id}")
            
            # Perform compression using existing engine
            compressed = await self.compression_engine.compress(
                session, turns, character_data
            )
            
            # Store result
            state.compressed_context = compressed
            state.compression_complete = True
            
            logger.info(f"Background compression completed for session {session_id}")
            
            # Emit completion event
            await self.event_system.emit(
                EventType.SYSTEM_STATUS,
                f"Background compression completed for session {session_id}",
                {
                    "session_id": session_id,
                    "compressed_tokens": compressed.get_token_count(),
                    "tokens_saved": compressed.compression_metadata.get("tokens_saved", 0)
                }
            )
            
        except Exception as e:
            logger.error(f"Background compression failed for session {session_id}: {e}")
            state.compression_complete = False
    
    async def collect_buffer_turn(
        self, 
        session_id: str, 
        turn: ConversationTurn
    ):
        """Collect turns in the buffer zone (75%-85%)"""
        state = self._get_or_create_state(session_id)
        
        # Only collect if compression has started but context hasn't reset
        if state.compression_started and turn.turn_id > state.started_at_turn:
            state.buffer_zone_turns.append(turn)
            logger.debug(f"Collected buffer turn {turn.turn_id} for session {session_id} "
                        f"(buffer size: {len(state.buffer_zone_turns)})")
    
    async def package_and_reset_context(
        self, 
        session_id: str,
        current_turns: List[ConversationTurn]
    ) -> CompressedContext:
        """At 85%: Package compressed + buffer + recent into new context"""
        state = self._get_or_create_state(session_id)
        
        try:
            logger.info(f"Packaging and resetting context for session {session_id}")
            
            # Wait for background compression if still running
            if state.compression_task and not state.compression_task.done():
                logger.info(f"Waiting for background compression to complete...")
                try:
                    await asyncio.wait_for(state.compression_task, timeout=30.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Background compression timeout for session {session_id}")
                    state.compression_complete = False
            
            # Start with compressed context if available
            if state.compression_complete and state.compressed_context:
                new_context = state.compressed_context
                logger.info(f"Using completed compressed context for session {session_id}")
            else:
                # Fallback: create minimal context
                logger.warning(f"Background compression not ready, creating minimal context")
                new_context = CompressedContext()
            
            # Add buffer zone turns to the context
            if state.buffer_zone_turns:
                new_context.buffer_turns = state.buffer_zone_turns.copy()
                logger.info(f"Added {len(state.buffer_zone_turns)} buffer turns to context")
            
            # Add recent turns (keep last N turns for immediate context)
            recent_turns = current_turns[-self.RECENT_TURNS_KEEP:] if current_turns else []
            new_context.recent_turns = recent_turns
            
            # Update compression metadata
            new_context.compression_metadata.update({
                "reset_at_turn": len(current_turns),
                "buffer_turns_count": len(state.buffer_zone_turns),
                "recent_turns_count": len(recent_turns),
                "compression_method": "buffer_zone_two_stage",
                "reset_timestamp": datetime.utcnow().isoformat()
            })
            
            # Emit reset event
            await self.event_system.emit(
                EventType.SYSTEM_STATUS,
                f"Context reset completed for session {session_id}",
                {
                    "session_id": session_id,
                    "buffer_turns": len(state.buffer_zone_turns),
                    "recent_turns": len(recent_turns),
                    "new_context_tokens": new_context.get_token_count()
                }
            )
            
            # Clean up state for next cycle
            self._reset_session_state(session_id)
            
            return new_context
            
        except Exception as e:
            logger.error(f"Failed to package context for session {session_id}: {e}")
            # Return minimal context on error
            return CompressedContext()
    
    def _reset_session_state(self, session_id: str):
        """Reset compression state for next cycle"""
        if session_id in self._compression_states:
            old_state = self._compression_states[session_id]
            
            # Cancel any running task
            if old_state.compression_task and not old_state.compression_task.done():
                old_state.compression_task.cancel()
            
            # Create fresh state
            self._compression_states[session_id] = CompressionState(session_id=session_id)
    
    async def get_compression_status(self, session_id: str, turns: List[ConversationTurn]) -> CompressionStatus:
        """Get current compression state for session"""
        state = self._get_or_create_state(session_id)
        percentage = self._calculate_token_percentage(turns)
        
        return CompressionStatus(
            session_id=session_id,
            token_percentage=percentage,
            compression_triggered=state.compression_started,
            compression_complete=state.compression_complete,
            buffer_zone_size=len(state.buffer_zone_turns),
            ready_for_reset=percentage >= self.CONTEXT_RESET_THRESHOLD,
            tokens_saved=state.compressed_context.compression_metadata.get("tokens_saved", 0) 
                        if state.compressed_context else 0
        )
    
    async def cleanup_session(self, session_id: str):
        """Clean up resources for a session"""
        if session_id in self._compression_states:
            state = self._compression_states[session_id]
            
            # Cancel any running compression task
            if state.compression_task and not state.compression_task.done():
                state.compression_task.cancel()
                try:
                    await state.compression_task
                except asyncio.CancelledError:
                    pass
            
            # Remove state
            del self._compression_states[session_id]
            logger.info(f"Cleaned up compression state for session {session_id}")
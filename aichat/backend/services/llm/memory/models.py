"""
Data models for the conversation memory system
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class ConversationSession:
    """Represents a conversation session between users and a character"""
    session_id: str = field(default_factory=lambda: str(uuid4()))
    character_id: int = 0
    character_name: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    participants: List[str] = field(default_factory=list)
    total_turns: int = 0
    compression_count: int = 0
    total_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation"""
    turn_id: int
    session_id: str
    speaker_id: str
    speaker_type: Literal["user", "assistant", "system"]
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "speaker_id": self.speaker_id,
            "speaker_type": self.speaker_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "token_count": self.token_count,
            "metadata": self.metadata,
            "importance_score": self.importance_score
        }


@dataclass
class ConversationSummary:
    """Represents a summary of conversation segment"""
    summary_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    summary_type: Literal["topic", "event", "fact", "emotion", "decision", "general"] = "general"
    content: str = ""
    turn_start: int = 0
    turn_end: int = 0
    participants: List[str] = field(default_factory=list)
    importance_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "summary_id": self.summary_id,
            "session_id": self.session_id,
            "summary_type": self.summary_type,
            "content": self.content,
            "turn_start": self.turn_start,
            "turn_end": self.turn_end,
            "participants": self.participants,
            "importance_score": self.importance_score,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class CompressedContext:
    """Represents compressed conversation context for LLM"""
    character_reminder: str = ""
    session_summary: str = ""
    key_topics: List[tuple[str, List[int]]] = field(default_factory=list)
    emotional_journey: str = ""
    important_facts: List[str] = field(default_factory=list)
    preserved_turns: List[ConversationTurn] = field(default_factory=list)
    recent_turns: List[ConversationTurn] = field(default_factory=list)
    buffer_turns: List[ConversationTurn] = field(default_factory=list)  # NEW: Buffer zone turns (75%-85%)
    compression_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_prompt(self) -> str:
        """Convert to prompt string for LLM"""
        prompt_parts = []
        
        # Character reminder always first
        if self.character_reminder:
            prompt_parts.append(self.character_reminder)
            prompt_parts.append("")
        
        # Conversation summary
        if self.session_summary:
            prompt_parts.append("CONVERSATION SUMMARY:")
            prompt_parts.append(self.session_summary)
            prompt_parts.append("")
        
        # Key topics with turn references
        if self.key_topics:
            prompt_parts.append("KEY MOMENTS:")
            for topic, turn_refs in self.key_topics:
                turns_str = ", ".join(f"Turn {t}" for t in turn_refs)
                prompt_parts.append(f"- {topic} ({turns_str})")
            prompt_parts.append("")
        
        # Emotional journey
        if self.emotional_journey:
            prompt_parts.append("EMOTIONAL JOURNEY:")
            prompt_parts.append(self.emotional_journey)
            prompt_parts.append("")
        
        # Important facts
        if self.important_facts:
            prompt_parts.append("IMPORTANT FACTS:")
            for fact in self.important_facts:
                prompt_parts.append(f"- {fact}")
            prompt_parts.append("")
        
        # Preserved important turns
        if self.preserved_turns:
            prompt_parts.append("PRESERVED TURNS:")
            for turn in self.preserved_turns:
                speaker = "User" if turn.speaker_type == "user" else turn.speaker_id
                prompt_parts.append(f'Turn {turn.turn_id} ({speaker}): "{turn.message}"')
            prompt_parts.append("")
        
        # Buffer zone turns (context bridge from compression to reset)
        if self.buffer_turns:
            prompt_parts.append(f"BUFFER CONTEXT (Transition period, {len(self.buffer_turns)} turns):")
            for turn in self.buffer_turns:
                speaker = "User" if turn.speaker_type == "user" else turn.speaker_id
                emotion = turn.metadata.get("emotion", "")
                emotion_tag = f"[{emotion}] " if emotion else ""
                prompt_parts.append(f'Turn {turn.turn_id} ({speaker}): {emotion_tag}"{turn.message}"')
            prompt_parts.append("")
        
        # Recent context (always last before current)
        if self.recent_turns:
            prompt_parts.append(f"RECENT CONTEXT (Last {len(self.recent_turns)} exchanges):")
            for turn in self.recent_turns:
                speaker = "User" if turn.speaker_type == "user" else turn.speaker_id
                emotion = turn.metadata.get("emotion", "")
                emotion_tag = f"[{emotion}] " if emotion else ""
                prompt_parts.append(f'Turn {turn.turn_id} ({speaker}): {emotion_tag}"{turn.message}"')
        
        return "\n".join(prompt_parts)
    
    def get_token_count(self) -> int:
        """Estimate token count of compressed context"""
        # Simple estimation: ~4 characters per token
        return len(self.to_prompt()) // 4


@dataclass
class CompressionEvent:
    """Records when and how compression occurred"""
    session_id: str
    compressed_at_turn: int
    original_token_count: int
    compressed_token_count: int
    preserved_turn_ids: List[int] = field(default_factory=list)
    summary: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "session_id": self.session_id,
            "compressed_at_turn": self.compressed_at_turn,
            "original_token_count": self.original_token_count,
            "compressed_token_count": self.compressed_token_count,
            "preserved_turn_ids": self.preserved_turn_ids,
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat()
        }
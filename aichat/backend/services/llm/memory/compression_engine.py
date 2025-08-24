"""
Intelligent conversation compression engine
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .models import (
    ConversationTurn, 
    CompressedContext, 
    ConversationSummary,
    CompressionEvent,
    ConversationSession
)
from ..summarization_model import create_intelligent_summary
from aichat.core.event_system import EventType, get_event_system

logger = logging.getLogger(__name__)


class CompressionEngine:
    """Handles intelligent conversation compression"""
    
    # Compression configuration
    COMPRESSION_CONFIG = {
        "compression_start_threshold": 0.75,  # 75% starts background compression
        "context_reset_threshold": 0.85,     # 85% triggers immediate context reset
        "recent_turns_keep": 10,              # Always keep last 10 turns
        "preserved_turns_budget": 1000,      # Tokens for important turns
        "character_reminder_tokens": 200,    # Character reinforcement
        "compression_frequency": 100,        # Force compress every 100 turns
        "min_importance_score": 5.0,         # Minimum score to preserve turn
        "context_window_size": 8000,         # Total context window
    }
    
    # Importance scoring weights
    IMPORTANCE_WEIGHTS = {
        "emotional_peak": 10,      # High emotion detected
        "decision_made": 8,        # User/character made decision
        "topic_introduction": 7,   # New topic introduced
        "user_information": 6,     # Personal info shared
        "character_defining": 5,   # Character trait expressed
        "question_asked": 4,       # Important question
        "humor_moment": 3,         # Funny exchange
        "conflict_resolution": 9,  # Resolved disagreement
    }
    
    def __init__(self):
        self.event_system = get_event_system()
    
    async def should_start_compression(
        self, 
        turns: List[ConversationTurn],
        current_tokens: int
    ) -> bool:
        """Check if background compression should start (75% threshold)"""
        
        config = self.COMPRESSION_CONFIG
        
        # Check 75% token threshold for starting compression
        start_threshold_tokens = int(config["context_window_size"] * config["compression_start_threshold"])
        if current_tokens >= start_threshold_tokens:
            return True
        
        # Check turn count threshold
        if len(turns) >= config["compression_frequency"]:
            return True
            
        return False
    
    async def should_reset_context(
        self, 
        turns: List[ConversationTurn],
        current_tokens: int
    ) -> bool:
        """Check if context should be reset immediately (85% threshold)"""
        
        config = self.COMPRESSION_CONFIG
        
        # Check 85% token threshold for context reset
        reset_threshold_tokens = int(config["context_window_size"] * config["context_reset_threshold"])
        if current_tokens >= reset_threshold_tokens:
            return True
            
        return False
    
    async def compress(
        self,
        session: ConversationSession,
        turns: List[ConversationTurn],
        character_data: Dict[str, str]
    ) -> CompressedContext:
        """Compress conversation into structured context"""
        
        logger.info(f"Compressing {len(turns)} turns for session {session.session_id}")
        
        # Convert turns to dict format for summarization model
        turn_dicts = [turn.to_dict() for turn in turns]
        
        # Generate intelligent summary using smart summarization model
        intelligent_summary = await create_intelligent_summary(
            conversation_turns=turn_dicts,
            character_name=character_data.get("name", "Character"),
            character_personality=character_data.get("personality", ""),
            character_profile=character_data.get("profile", ""),
            session_metadata={"total_turns": session.total_turns, "compression_count": session.compression_count}
        )
        
        # Use intelligent scoring to select preserved turns
        preserved_turns = await self._select_preserved_turns_intelligently(turns, intelligent_summary)
        
        # Get recent turns (always keep)
        recent_turns = turns[-self.COMPRESSION_CONFIG["recent_turns_keep"]:]
        
        # Build enhanced character reminder with intelligent analysis
        character_reminder = await self._build_intelligent_character_reminder(
            character_data, 
            session,
            intelligent_summary
        )
        
        # Create compressed context with intelligent summary
        compressed = CompressedContext(
            character_reminder=character_reminder,
            session_summary=intelligent_summary.summary,
            key_topics=[(f"{moment.reason} (Turn {moment.turn_id})", [moment.turn_id]) for moment in intelligent_summary.key_moments],
            emotional_journey=intelligent_summary.emotional_journey,
            important_facts=intelligent_summary.user_revealed_info + [f"Topics covered: {', '.join(intelligent_summary.topic_progression)}"],
            preserved_turns=preserved_turns,
            recent_turns=recent_turns,
            compression_metadata={
                "original_turn_count": len(turns),
                "compressed_at_turn": turns[-1].turn_id if turns else 0,
                "compression_number": session.compression_count + 1,
                "tokens_saved": 0,  # Will calculate below
                "preserved_turn_ids": [t.turn_id for t in preserved_turns],
                "timestamp": datetime.utcnow().isoformat(),
                "relationship_evolution": intelligent_summary.relationship_evolution,
                "character_consistency_score": intelligent_summary.character_consistency.personality_score,
                "summarization_model_used": True
            }
        )
        
        # Calculate tokens saved
        original_tokens = sum(t.token_count for t in turns)
        compressed_tokens = self._estimate_compressed_tokens(compressed)
        compressed.compression_metadata["tokens_saved"] = original_tokens - compressed_tokens
        
        # Record compression event
        await self._record_compression_event(session, compressed, turns)
        
        # Emit event
        await self.event_system.emit(
            EventType.SYSTEM_STATUS,
            f"Conversation compressed: {len(turns)} turns → {len(preserved_turns)} preserved",
            {
                "session_id": session.session_id,
                "original_turns": len(turns),
                "preserved_turns": len(preserved_turns),
                "tokens_saved": compressed.compression_metadata["tokens_saved"]
            }
        )
        
        return compressed
    
    async def _generate_summary_with_examples(self, turns: List[ConversationTurn]) -> Dict:
        """Generate summary using LLM with specific examples"""
        
        # Build conversation text
        conversation_text = self._format_turns_for_summary(turns)
        
        # Create prompt with examples
        prompt = self._build_compression_prompt_with_examples(conversation_text)
        
        # Use cheap model for summarization
        try:
            # Get OpenRouter service (we'll need to import this)
            from aichat.backend.services.llm.openrouter_service import OpenRouterService
            llm_service = OpenRouterService()
            
            # Use cheapest model for summarization
            cheap_model = "mistralai/mistral-7b-instruct"  # $0.06/1M tokens
            
            response = await llm_service.generate_response(
                message=prompt,
                character_name="System",
                character_personality="analytical",
                character_profile="summarizer",
                model=cheap_model,
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=500
            )
            
            # Parse the response
            return self._parse_summary_response(response["response"])
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            # Fallback to basic summary
            return {
                "summary": f"Conversation with {len(turns)} exchanges.",
                "key_moments": [],
                "emotional": "neutral",
                "facts": [],
                "decisions": []
            }
    
    def _build_compression_prompt_with_examples(self, conversation_text: str) -> str:
        """Build compression prompt with concrete examples"""
        
        return f"""Compress this conversation following this EXACT format:

EXAMPLE INPUT:
User: "I lost my job today"
Assistant: "I'm so sorry to hear that"
User: "I don't know what to do"
Assistant: "What field do you work in?"
User: "Software development"
Assistant: "The tech market is tough but your skills are valuable"
User: "I have a family to support"
Assistant: "Have you looked at your emergency savings?"
User: "We have 3 months saved"
Assistant: "That's a good buffer. You can be strategic"

EXAMPLE OUTPUT:
SUMMARY: User lost software development job, worried about family. Has 3 months savings.
KEY_MOMENTS: Turn 1 (job loss), Turn 7 (family pressure), Turn 9 (savings confirmed)
EMOTIONAL: Distressed → Worried → Slightly relieved
FACTS: Unemployed software developer, has family, 3 months savings
DECISIONS: Will be strategic about job search

NOW COMPRESS THIS CONVERSATION:
{conversation_text}

OUTPUT:"""
    
    def _format_turns_for_summary(self, turns: List[ConversationTurn]) -> str:
        """Format turns for summarization"""
        
        lines = []
        for turn in turns:
            speaker = "User" if turn.speaker_type == "user" else "Assistant"
            lines.append(f'{speaker}: "{turn.message}"')
        
        return "\n".join(lines)
    
    def _parse_summary_response(self, response: str) -> Dict:
        """Parse structured summary from LLM response"""
        
        result = {
            "summary": "",
            "key_moments": [],
            "emotional": "",
            "facts": [],
            "decisions": []
        }
        
        lines = response.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if line.startswith("SUMMARY:"):
                result["summary"] = line[8:].strip()
            elif line.startswith("KEY_MOMENTS:"):
                result["key_moments"] = self._parse_key_moments(line[12:].strip())
            elif line.startswith("EMOTIONAL:"):
                result["emotional"] = line[10:].strip()
            elif line.startswith("FACTS:"):
                result["facts"] = [f.strip() for f in line[6:].split(",")]
            elif line.startswith("DECISIONS:"):
                result["decisions"] = [d.strip() for d in line[10:].split(",")]
        
        return result
    
    def _parse_key_moments(self, text: str) -> List[Tuple[int, str]]:
        """Parse key moments with turn references"""
        
        moments = []
        import re
        
        # Pattern: Turn X (description)
        pattern = r'Turn (\d+) \(([^)]+)\)'
        matches = re.findall(pattern, text)
        
        for turn_num, description in matches:
            moments.append((int(turn_num), description))
        
        return moments
    
    async def _score_all_turns(self, turns: List[ConversationTurn]) -> List[Tuple[float, ConversationTurn]]:
        """Score all turns for importance"""
        
        scored = []
        
        for i, turn in enumerate(turns):
            score = await self._score_turn(turn, i, len(turns))
            scored.append((score, turn))
            turn.importance_score = score  # Store in turn object
        
        # Sort by score (highest first)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return scored
    
    async def _score_turn(self, turn: ConversationTurn, position: int, total_turns: int) -> float:
        """Score a single turn for importance"""
        
        score = 0.0
        
        # Check for importance factors
        message_lower = turn.message.lower()
        
        # Emotional peaks
        if any(word in message_lower for word in ["excited", "sad", "angry", "happy", "love"]):
            score += self.IMPORTANCE_WEIGHTS["emotional_peak"]
        
        # Decisions
        if any(word in message_lower for word in ["decided", "will", "going to", "plan to"]):
            score += self.IMPORTANCE_WEIGHTS["decision_made"]
        
        # Questions
        if "?" in turn.message:
            score += self.IMPORTANCE_WEIGHTS["question_asked"]
        
        # User information
        if turn.speaker_type == "user" and any(word in message_lower for word in ["i am", "i work", "my name", "i live"]):
            score += self.IMPORTANCE_WEIGHTS["user_information"]
        
        # Recency bonus
        recency_position = total_turns - position
        if recency_position <= 5:
            score += 5
        elif recency_position <= 10:
            score += 3
        elif recency_position <= 20:
            score += 1
        
        # Metadata factors
        if "emotion" in turn.metadata:
            emotion = turn.metadata["emotion"]
            if emotion not in ["neutral", "calm"]:
                score += 2
        
        return score
    
    async def _select_preserved_turns(
        self, 
        scored_turns: List[Tuple[float, ConversationTurn]]
    ) -> List[ConversationTurn]:
        """Select turns to preserve within token budget"""
        
        preserved = []
        token_count = 0
        max_tokens = self.COMPRESSION_CONFIG["preserved_turns_budget"]
        min_score = self.COMPRESSION_CONFIG["min_importance_score"]
        
        for score, turn in scored_turns:
            # Skip if score too low
            if score < min_score:
                continue
                
            # Estimate tokens (rough: 1 token per 4 characters)
            turn_tokens = len(turn.message) // 4
            
            if token_count + turn_tokens <= max_tokens:
                preserved.append(turn)
                token_count += turn_tokens
            
            # Stop if we've filled our budget
            if token_count >= max_tokens:
                break
        
        # Sort by turn ID to maintain chronological order
        preserved.sort(key=lambda t: t.turn_id)
        
        return preserved
    
    async def _extract_key_topics(
        self, 
        turns: List[ConversationTurn],
        summary_data: Dict
    ) -> List[Tuple[str, List[int]]]:
        """Extract key topics with turn references"""
        
        topics = []
        
        # Use key moments from summary if available
        if "key_moments" in summary_data:
            for turn_num, description in summary_data["key_moments"]:
                topics.append((description, [turn_num]))
        
        return topics
    
    async def _extract_emotional_journey(self, turns: List[ConversationTurn]) -> str:
        """Extract emotional journey from turns"""
        
        emotions = []
        
        for turn in turns:
            if turn.speaker_type == "assistant" and "emotion" in turn.metadata:
                emotion = turn.metadata["emotion"]
                if not emotions or emotions[-1] != emotion:
                    emotions.append(emotion)
        
        if emotions:
            return " → ".join(emotions)
        
        return "neutral throughout"
    
    async def _extract_important_facts(
        self, 
        turns: List[ConversationTurn],
        summary_data: Dict
    ) -> List[str]:
        """Extract important facts from conversation"""
        
        facts = []
        
        # Use facts from summary if available
        if "facts" in summary_data:
            facts.extend(summary_data["facts"])
        
        # Add decisions as facts
        if "decisions" in summary_data:
            for decision in summary_data["decisions"]:
                facts.append(f"Decision: {decision}")
        
        return facts[:10]  # Limit to 10 most important facts
    
    async def _build_character_reminder(
        self,
        character_data: Dict[str, str],
        session: ConversationSession,
        summary_data: Dict
    ) -> str:
        """Build character reminder with context"""
        
        template = """You are {name}, the {profile_brief}.

CORE TRAITS: {personality}

CONVERSATION CONTEXT:
- Talking for {turn_count} exchanges
- Main topics: {topics}
- Emotional state: {emotional_state}
- Relationship: {relationship}

Remember to maintain your personality while being responsive to the conversation context."""
        
        # Extract brief profile
        profile_brief = character_data.get("profile", "").split(".")[0]
        
        # Get topics from summary
        topics = summary_data.get("summary", "various topics")[:100]
        
        # Get emotional state
        emotional_state = summary_data.get("emotional", "engaged")
        
        return template.format(
            name=character_data.get("name", "Assistant"),
            profile_brief=profile_brief,
            personality=character_data.get("personality", "helpful and friendly"),
            turn_count=session.total_turns,
            topics=topics,
            emotional_state=emotional_state,
            relationship="developing friendship"
        )
    
    def _estimate_compressed_tokens(self, compressed: CompressedContext) -> int:
        """Estimate token count of compressed context"""
        
        return compressed.get_token_count()
    
    async def _record_compression_event(
        self,
        session: ConversationSession,
        compressed: CompressedContext,
        original_turns: List[ConversationTurn]
    ):
        """Record compression event in database"""
        
        event = CompressionEvent(
            session_id=session.session_id,
            compressed_at_turn=original_turns[-1].turn_id if original_turns else 0,
            original_token_count=sum(t.token_count for t in original_turns),
            compressed_token_count=compressed.get_token_count(),
            preserved_turn_ids=[t.turn_id for t in compressed.preserved_turns],
            summary=compressed.session_summary
        )
        
        # Store in database (implementation depends on db_ops)
        logger.info(f"Recorded compression event for session {session.session_id}")
    
    async def _select_preserved_turns_intelligently(
        self, 
        turns: List[ConversationTurn],
        intelligent_summary
    ) -> List[ConversationTurn]:
        """Select turns to preserve using intelligent analysis"""
        
        preserved = []
        
        # Always preserve key moments from intelligent analysis
        key_turn_ids = [moment.turn_id for moment in intelligent_summary.key_moments]
        
        # Also preserve notable character moments
        notable_turn_ids = intelligent_summary.character_consistency.notable_moments
        
        # Combine and deduplicate important turn IDs
        important_turn_ids = set(key_turn_ids + notable_turn_ids)
        
        # Find corresponding turns
        for turn in turns:
            if turn.turn_id in important_turn_ids:
                preserved.append(turn)
        
        # Sort by turn ID to maintain chronological order
        preserved.sort(key=lambda t: t.turn_id)
        
        logger.info(f"Selected {len(preserved)} turns for preservation based on intelligent analysis")
        return preserved
    
    async def _build_intelligent_character_reminder(
        self,
        character_data: Dict[str, str],
        session: ConversationSession,
        intelligent_summary
    ) -> str:
        """Build character reminder using intelligent summary"""
        
        template = """You are {name}.

CORE PERSONALITY: {personality}
BACKGROUND: {profile}

CONVERSATION INTELLIGENCE:
- Summary: {summary}
- Relationship Evolution: {relationship}
- Your Emotional Journey: {emotional_journey}
- Character Traits You've Shown: {traits_shown}
- Character Performance Score: {performance_score:.1f}/1.0

IMPORTANT USER INFO TO REMEMBER:
{user_info}

CONVERSATION DYNAMICS:
- Topics Discussed: {topics}
- Key Moments: {key_moments}

Continue being {name} while maintaining the relationship dynamic and remembering what you've learned about the user."""
        
        # Format key moments
        key_moments_text = []
        for moment in intelligent_summary.key_moments[:3]:  # Top 3 moments
            key_moments_text.append(f"Turn {moment.turn_id}: {moment.reason}")
        key_moments_str = "; ".join(key_moments_text) if key_moments_text else "Various interactions"
        
        # Format user info
        user_info_str = "; ".join(intelligent_summary.user_revealed_info) if intelligent_summary.user_revealed_info else "General conversation"
        
        # Format traits shown
        traits_shown_str = ", ".join(intelligent_summary.character_consistency.traits_expressed) if intelligent_summary.character_consistency.traits_expressed else "various traits"
        
        return template.format(
            name=character_data.get("name", "Assistant"),
            personality=character_data.get("personality", "helpful and friendly"),
            profile=character_data.get("profile", "AI assistant")[:200],  # Truncate for brevity
            summary=intelligent_summary.summary[:300],  # Truncate summary
            relationship=intelligent_summary.relationship_evolution,
            emotional_journey=intelligent_summary.emotional_journey,
            traits_shown=traits_shown_str,
            performance_score=intelligent_summary.character_consistency.personality_score,
            user_info=user_info_str,
            topics=", ".join(intelligent_summary.topic_progression),
            key_moments=key_moments_str
        )
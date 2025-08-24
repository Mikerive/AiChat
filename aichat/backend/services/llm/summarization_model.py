"""
Smart Summarization Model

Intelligent conversation compression with reasoning capabilities.
Used during memory compression events to preserve important context.
"""

import logging
import os
import json
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class KeyMoment:
    """Important moment in conversation with reasoning"""
    turn_id: int
    importance_score: float  # 0.0-1.0
    reason: str             # Why this moment is important
    participants: List[str]  # Who was involved
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "importance_score": self.importance_score,
            "reason": self.reason,
            "participants": self.participants
        }


@dataclass
class CharacterConsistency:
    """Analysis of character consistency"""
    traits_expressed: List[str]      # Which personality traits were shown
    personality_score: float         # How well character stayed in character (0.0-1.0)
    notable_moments: List[int]       # Turn IDs where character was particularly good
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "traits_expressed": self.traits_expressed,
            "personality_score": self.personality_score,
            "notable_moments": self.notable_moments
        }


@dataclass
class ConversationSummary:
    """Comprehensive conversation analysis"""
    summary: str                                    # Main conversation summary
    emotional_journey: str                          # How emotions evolved
    key_moments: List[KeyMoment]                   # Most important turns
    relationship_evolution: str                     # How relationship changed
    character_consistency: CharacterConsistency    # Character performance analysis
    topic_progression: List[str]                   # How topics evolved
    user_revealed_info: List[str]                  # Important things user shared
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "emotional_journey": self.emotional_journey,
            "key_moments": [moment.to_dict() for moment in self.key_moments],
            "relationship_evolution": self.relationship_evolution,
            "character_consistency": self.character_consistency.to_dict(),
            "topic_progression": self.topic_progression,
            "user_revealed_info": self.user_revealed_info
        }


class SummarizationModel:
    """Smart summarization model for conversation compression"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenRouter API key"""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.session = None
        
        # Use better model for summarization - needs reasoning capabilities
        self.summary_model = "openai/gpt-4o-mini"  # $0.15/1M tokens, good reasoning
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aichat.local",
                "X-Title": "AiChat Summarization Model",
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def analyze_conversation(
        self,
        conversation_turns: List[Dict[str, Any]],
        character_name: str,
        character_personality: str,
        character_profile: str,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationSummary:
        """
        Perform intelligent analysis of full conversation for compression.
        This creates rich, reasoned summaries that preserve important context.
        """
        
        try:
            if not self.api_key:
                logger.warning("No API key for summarization model, using basic summary")
                return self._create_basic_summary(conversation_turns)
            
            # Build comprehensive analysis prompt
            prompt = self._build_summarization_prompt(
                conversation_turns, character_name, character_personality, 
                character_profile, session_metadata
            )
            
            payload = {
                "model": self.summary_model,
                "messages": [
                    {"role": "system", "content": "You are an expert conversation analyst. Provide detailed, reasoned analysis in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,  # Some creativity but mostly consistent
                "max_tokens": 1000,  # Enough for comprehensive analysis
            }
            
            session = await self._get_session()
            async with session.post(f"{self.base_url}/chat/completions", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        analysis_text = result["choices"][0]["message"]["content"].strip()
                        return self._parse_summarization_response(analysis_text, conversation_turns)
                        
                logger.warning("No summarization received from API")
                return self._create_basic_summary(conversation_turns)
                
        except Exception as e:
            logger.error(f"Error in summarization model: {e}")
            return self._create_basic_summary(conversation_turns)
    
    def _build_summarization_prompt(
        self,
        conversation_turns: List[Dict[str, Any]],
        character_name: str,
        character_personality: str,
        character_profile: str,
        session_metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Build comprehensive summarization prompt"""
        
        # Format conversation for analysis
        conversation_text = self._format_conversation(conversation_turns)
        
        metadata_part = ""
        if session_metadata:
            metadata_part = f"\n\nSession info: {json.dumps(session_metadata, indent=2)}"
        
        return f"""Analyze this conversation comprehensively for intelligent compression.

CHARACTER: {character_name}
PERSONALITY: {character_personality}
PROFILE: {character_profile}

CONVERSATION ({len(conversation_turns)} turns):
{conversation_text}{metadata_part}

Provide detailed analysis as JSON with this EXACT structure:
{{
  "summary": "Rich narrative summary of what happened, focusing on meaningful interactions",
  "emotional_journey": "How emotions evolved throughout conversation (e.g., 'started curious → became excited → ended thoughtful')",
  "key_moments": [
    {{
      "turn_id": 5,
      "importance_score": 0.9,
      "reason": "Specific reason why this turn matters for character/relationship continuity",
      "participants": ["user", "{character_name}"]
    }}
  ],
  "relationship_evolution": "How the relationship between user and character changed",
  "character_consistency": {{
    "traits_expressed": ["list of personality traits that were shown"],
    "personality_score": 0.8,
    "notable_moments": [turn_ids where character was particularly well-expressed]
  }},
  "topic_progression": ["list of topics in order they appeared"],
  "user_revealed_info": ["important personal info user shared that character should remember"]
}}

ANALYSIS GUIDELINES:
- summary: Tell the story of this conversation - what really happened that matters
- key_moments: Identify 3-5 most important turns with HIGH importance scores (0.7+) and clear reasons
- Focus on moments that: establish relationship, reveal character, show emotional growth, contain important decisions
- character_consistency: How well did {character_name} maintain their personality? What traits shone through?
- relationship_evolution: Did they become closer? More formal? Did dynamic change?
- user_revealed_info: Personal details, preferences, goals, problems user shared

Respond with ONLY the JSON:"""
    
    def _format_conversation(self, turns: List[Dict[str, Any]]) -> str:
        """Format conversation turns for analysis"""
        
        formatted_lines = []
        for i, turn in enumerate(turns):
            turn_id = turn.get("turn_id", i + 1)
            speaker = turn.get("speaker_id", "unknown")
            speaker_type = turn.get("speaker_type", "unknown")
            message = turn.get("message", "")
            
            # Format speaker name
            if speaker_type == "user":
                speaker_name = "User"
            else:
                speaker_name = speaker
                
            formatted_lines.append(f"Turn {turn_id} ({speaker_name}): {message}")
        
        return "\n".join(formatted_lines)
    
    def _parse_summarization_response(
        self, 
        response_text: str, 
        conversation_turns: List[Dict[str, Any]]
    ) -> ConversationSummary:
        """Parse comprehensive analysis response"""
        
        try:
            # Clean up response text
            response_text = response_text.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Parse key moments
            key_moments = []
            for moment_data in data.get("key_moments", []):
                try:
                    key_moments.append(KeyMoment(
                        turn_id=int(moment_data.get("turn_id", 0)),
                        importance_score=max(0.0, min(1.0, float(moment_data.get("importance_score", 0.5)))),
                        reason=str(moment_data.get("reason", "Important moment")),
                        participants=moment_data.get("participants", ["user", "assistant"])
                    ))
                except (KeyError, ValueError, TypeError):
                    continue
            
            # Parse character consistency
            consistency_data = data.get("character_consistency", {})
            character_consistency = CharacterConsistency(
                traits_expressed=consistency_data.get("traits_expressed", []),
                personality_score=max(0.0, min(1.0, float(consistency_data.get("personality_score", 0.5)))),
                notable_moments=consistency_data.get("notable_moments", [])
            )
            
            return ConversationSummary(
                summary=data.get("summary", f"Conversation with {len(conversation_turns)} exchanges"),
                emotional_journey=data.get("emotional_journey", "neutral throughout"),
                key_moments=key_moments,
                relationship_evolution=data.get("relationship_evolution", "maintained consistent dynamic"),
                character_consistency=character_consistency,
                topic_progression=data.get("topic_progression", ["general conversation"]),
                user_revealed_info=data.get("user_revealed_info", [])
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse summarization response: {e}")
            logger.debug(f"Response text was: {response_text}")
            return self._create_basic_summary(conversation_turns)
    
    def _create_basic_summary(self, conversation_turns: List[Dict[str, Any]]) -> ConversationSummary:
        """Create basic summary when model is unavailable"""
        
        return ConversationSummary(
            summary=f"Conversation with {len(conversation_turns)} exchanges",
            emotional_journey="varied emotions throughout",
            key_moments=[],
            relationship_evolution="ongoing conversation",
            character_consistency=CharacterConsistency(
                traits_expressed=[],
                personality_score=0.5,
                notable_moments=[]
            ),
            topic_progression=["general conversation"],
            user_revealed_info=[]
        )
    
    async def score_turn_importance(
        self,
        turn_data: Dict[str, Any],
        conversation_context: List[Dict[str, Any]],
        character_info: Dict[str, str]
    ) -> float:
        """
        Score individual turn importance for selective preservation.
        This is used for fine-grained importance scoring during compression.
        """
        
        try:
            # Build focused importance scoring prompt
            prompt = self._build_importance_prompt(turn_data, conversation_context, character_info)
            
            payload = {
                "model": self.summary_model,
                "messages": [
                    {"role": "system", "content": "You are an importance scorer. Respond with ONLY a number between 0.0 and 1.0"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 10,
            }
            
            session = await self._get_session()
            async with session.post(f"{self.base_url}/chat/completions", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        score_text = result["choices"][0]["message"]["content"].strip()
                        try:
                            return max(0.0, min(1.0, float(score_text)))
                        except ValueError:
                            pass
                            
        except Exception as e:
            logger.error(f"Error scoring turn importance: {e}")
        
        return 0.5  # Default medium importance
    
    def _build_importance_prompt(
        self,
        turn_data: Dict[str, Any],
        conversation_context: List[Dict[str, Any]],
        character_info: Dict[str, str]
    ) -> str:
        """Build prompt for scoring individual turn importance"""
        
        message = turn_data.get("message", "")
        speaker_type = turn_data.get("speaker_type", "unknown")
        turn_id = turn_data.get("turn_id", 0)
        
        context_snippet = ""
        if conversation_context:
            recent_turns = conversation_context[-3:]  # Last 3 turns for context
            context_lines = []
            for turn in recent_turns:
                speaker = "User" if turn.get("speaker_type") == "user" else "Character"
                context_lines.append(f"{speaker}: {turn.get('message', '')}")
            context_snippet = "\n".join(context_lines)
        
        return f"""Rate the importance of preserving this turn for character continuity (0.0 = not important, 1.0 = critical).

CHARACTER: {character_info.get('name', 'Character')}
PERSONALITY: {character_info.get('personality', 'Unknown')}

CONTEXT:
{context_snippet}

TURN TO SCORE:
Turn {turn_id} ({'User' if speaker_type == 'user' else 'Character'}): {message}

Score this turn's importance for:
- Character development/consistency
- Relationship building  
- Plot/story progression
- Emotional significance
- Information revelation

Respond with ONLY a number (0.0-1.0):"""


# Global instance
_summarization_model = None

def get_summarization_model() -> SummarizationModel:
    """Get global summarization model instance"""
    global _summarization_model
    if _summarization_model is None:
        _summarization_model = SummarizationModel()
    return _summarization_model

async def create_intelligent_summary(
    conversation_turns: List[Dict[str, Any]],
    character_name: str,
    character_personality: str,
    character_profile: str,
    session_metadata: Optional[Dict[str, Any]] = None
) -> ConversationSummary:
    """
    Convenience function to create intelligent conversation summary.
    Used during compression events.
    """
    summarizer = get_summarization_model()
    return await summarizer.analyze_conversation(
        conversation_turns, character_name, character_personality,
        character_profile, session_metadata
    )
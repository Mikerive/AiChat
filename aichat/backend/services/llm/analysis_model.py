"""
Real-time Analysis Model

Fast, lightweight model for generating all metadata needed for TTS and response generation.
Acts as a bridge between conversation and voice synthesis.
"""

import logging
import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class VoiceParameters:
    """Voice synthesis parameters"""
    speed: float = 1.0      # 0.5-2.0x normal speed
    pitch: float = 0.0      # -20 to +20 semitones
    volume: str = "normal"  # quiet, normal, loud
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "speed": self.speed,
            "pitch": self.pitch, 
            "volume": self.volume
        }


@dataclass
class ConversationAnalysis:
    """Analysis of conversation state"""
    topic_change: bool = False
    question_type: str = "general"     # info, personal, hypothetical, rhetorical
    user_mood: str = "neutral"         # happy, sad, excited, etc.
    engagement_level: str = "medium"   # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic_change": self.topic_change,
            "question_type": self.question_type,
            "user_mood": self.user_mood,
            "engagement_level": self.engagement_level
        }


@dataclass
class ResponseMetadata:
    """Complete metadata package for response generation"""
    emotion: str = "neutral"
    intensity: float = 0.5              # 0.0-1.0 for TTS exaggeration
    response_tone: str = "casual"       # formal, casual, playful, serious
    energy_level: str = "medium"        # low, medium, high, hyper
    voice_params: VoiceParameters = None
    conversation_analysis: ConversationAnalysis = None
    memory_context: list = None          # NEW: Memory search results
    
    def __post_init__(self):
        if self.voice_params is None:
            self.voice_params = VoiceParameters()
        if self.conversation_analysis is None:
            self.conversation_analysis = ConversationAnalysis()
        if self.memory_context is None:
            self.memory_context = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "emotion": self.emotion,
            "intensity": self.intensity,
            "response_tone": self.response_tone,
            "energy_level": self.energy_level,
            "voice_params": self.voice_params.to_dict(),
            "conversation_analysis": self.conversation_analysis.to_dict(),
            "memory_context": self.memory_context
        }


class AnalysisModel:
    """Fast analysis model for real-time metadata generation"""
    
    # Standard emotions
    EMOTIONS = [
        "neutral", "happy", "sad", "angry", "excited", 
        "surprised", "confused", "calm", "anxious", "thoughtful"
    ]
    
    # Response tones
    TONES = ["formal", "casual", "playful", "serious", "intimate", "professional"]
    
    # Energy levels  
    ENERGY_LEVELS = ["low", "medium", "high", "hyper"]
    
    # Question types
    QUESTION_TYPES = ["info", "personal", "hypothetical", "rhetorical", "general"]
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenRouter API key"""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.session = None
        
        # Use fast, cheap model for analysis
        self.analysis_model = "mistralai/mistral-7b-instruct"  # $0.06/1M tokens
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aichat.local",
                "X-Title": "AiChat Analysis Model",
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def analyze_conversation_state(
        self,
        user_message: str,
        character_name: str,
        character_personality: str,
        conversation_context: str = "",
        previous_metadata: Optional[ResponseMetadata] = None
    ) -> ResponseMetadata:
        """
        Analyze conversation and generate complete metadata for response generation.
        This is called before the main conversation model.
        """
        
        try:
            if not self.api_key:
                logger.warning("No API key for analysis model, using defaults")
                return ResponseMetadata()
            
            # Build analysis prompt
            prompt = self._build_analysis_prompt(
                user_message, character_name, character_personality, 
                conversation_context, previous_metadata
            )
            
            payload = {
                "model": self.analysis_model,
                "messages": [
                    {"role": "system", "content": "You are a conversation analyst. Respond with ONLY valid JSON, no other text."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,  # Low temperature for consistency
                "max_tokens": 200,   # Enough for JSON response
            }
            
            session = await self._get_session()
            async with session.post(f"{self.base_url}/chat/completions", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        analysis_text = result["choices"][0]["message"]["content"].strip()
                        return self._parse_analysis_response(analysis_text)
                        
                logger.warning("No analysis received from API")
                return ResponseMetadata()
                
        except Exception as e:
            logger.error(f"Error in analysis model: {e}")
            return ResponseMetadata()
    
    def _build_analysis_prompt(
        self,
        user_message: str,
        character_name: str,
        character_personality: str,
        conversation_context: str,
        previous_metadata: Optional[ResponseMetadata]
    ) -> str:
        """Build comprehensive analysis prompt"""
        
        context_part = f"\n\nRecent conversation:\n{conversation_context}" if conversation_context else ""
        
        previous_part = ""
        if previous_metadata:
            previous_part = f"\n\nPrevious response metadata:\n{json.dumps(previous_metadata.to_dict(), indent=2)}"
        
        return f"""Analyze this conversation situation and provide metadata for {character_name}'s response.

CHARACTER: {character_name}
PERSONALITY: {character_personality}
USER MESSAGE: "{user_message}"{context_part}{previous_part}

Generate analysis as JSON with this EXACT structure:
{{
  "emotion": "one of: {', '.join(self.EMOTIONS)}",
  "intensity": 0.5,
  "response_tone": "one of: {', '.join(self.TONES)}",
  "energy_level": "one of: {', '.join(self.ENERGY_LEVELS)}",
  "voice_params": {{
    "speed": 1.0,
    "pitch": 0.0,
    "volume": "normal"
  }},
  "conversation_analysis": {{
    "topic_change": false,
    "question_type": "one of: {', '.join(self.QUESTION_TYPES)}",
    "user_mood": "one of: {', '.join(self.EMOTIONS)}",
    "engagement_level": "low/medium/high"
  }}
}}

GUIDELINES:
- emotion: What {character_name} should feel about this message
- intensity: 0.0 (flat) to 1.0 (maximum expression) for TTS
- response_tone: How formal/casual the response should be
- energy_level: Character's energy for this response
- voice_params: speed (0.5-2.0), pitch (-20 to +20), volume (quiet/normal/loud)
- topic_change: Did user change the subject?
- question_type: What kind of question/statement is this?
- user_mood: What emotion is the user showing?
- engagement_level: How engaged is the user?

Respond with ONLY the JSON:"""
    
    def _parse_analysis_response(self, response_text: str) -> ResponseMetadata:
        """Parse JSON response into metadata object"""
        
        try:
            # Clean up response text
            response_text = response_text.strip()
            
            # Find JSON content
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Validate and create metadata
            return ResponseMetadata(
                emotion=self._validate_choice(data.get("emotion", "neutral"), self.EMOTIONS),
                intensity=max(0.0, min(1.0, float(data.get("intensity", 0.5)))),
                response_tone=self._validate_choice(data.get("response_tone", "casual"), self.TONES),
                energy_level=self._validate_choice(data.get("energy_level", "medium"), self.ENERGY_LEVELS),
                voice_params=self._parse_voice_params(data.get("voice_params", {})),
                conversation_analysis=self._parse_conversation_analysis(data.get("conversation_analysis", {}))
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse analysis response: {e}")
            logger.debug(f"Response text was: {response_text}")
            return ResponseMetadata()  # Return defaults
    
    def _validate_choice(self, value: str, valid_choices: list) -> str:
        """Validate that choice is in allowed list"""
        if isinstance(value, str) and value.lower() in [choice.lower() for choice in valid_choices]:
            return value.lower()
        return valid_choices[0]  # Return first choice as default
    
    def _parse_voice_params(self, data: Dict[str, Any]) -> VoiceParameters:
        """Parse voice parameters from JSON"""
        try:
            return VoiceParameters(
                speed=max(0.5, min(2.0, float(data.get("speed", 1.0)))),
                pitch=max(-20.0, min(20.0, float(data.get("pitch", 0.0)))),
                volume=self._validate_choice(data.get("volume", "normal"), ["quiet", "normal", "loud"])
            )
        except (KeyError, ValueError):
            return VoiceParameters()
    
    def _parse_conversation_analysis(self, data: Dict[str, Any]) -> ConversationAnalysis:
        """Parse conversation analysis from JSON"""
        try:
            return ConversationAnalysis(
                topic_change=bool(data.get("topic_change", False)),
                question_type=self._validate_choice(data.get("question_type", "general"), self.QUESTION_TYPES),
                user_mood=self._validate_choice(data.get("user_mood", "neutral"), self.EMOTIONS),
                engagement_level=self._validate_choice(data.get("engagement_level", "medium"), ["low", "medium", "high"])
            )
        except (KeyError, ValueError):
            return ConversationAnalysis()
    
    async def _search_memory_if_needed(
        self, 
        user_message: str, 
        memory_manager: Any, 
        session_id: str
    ) -> list:
        """
        Analyze user message to determine if memory search is needed.
        If so, extract search query and perform the search.
        """
        try:
            # Quick heuristic check for memory-related queries
            memory_indicators = [
                # Direct references
                "remember", "recall", "earlier", "before", "previously", "mentioned",
                # Questions about past
                "what did", "when did", "how did", "where did", "why did",
                "did we", "did you", "did i", "have we", "have you", "have i",
                # Temporal references
                "yesterday", "last time", "ago", "back when", "that time",
                # Conversation references
                "talked about", "discussed", "said", "told", "conversation"
            ]
            
            user_lower = user_message.lower()
            needs_memory = any(indicator in user_lower for indicator in memory_indicators)
            
            if not needs_memory:
                return []
            
            logger.info(f"Analysis model detected memory reference in: '{user_message}'")
            
            # Extract search query - use key parts of the message
            search_query = self._extract_search_query(user_message)
            
            # Perform memory search
            if search_query:
                search_results = await memory_manager.search_memories(
                    query=search_query,
                    session_id=session_id,
                    limit=5
                )
                
                logger.info(f"Memory search for '{search_query}' returned {len(search_results)} results")
                return search_results
            
            return []
            
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []
    
    def _extract_search_query(self, user_message: str) -> str:
        """Extract search query from user message"""
        # Simple extraction - remove common question words and focus on content
        query = user_message.lower()
        
        # Remove common question starters
        remove_patterns = [
            "do you remember", "can you recall", "what did", "when did",
            "how did", "where did", "why did", "did we", "did you", "did i",
            "have we", "have you", "have i", "tell me about", "remind me"
        ]
        
        for pattern in remove_patterns:
            if pattern in query:
                query = query.replace(pattern, "").strip()
        
        # Remove question marks and clean up
        query = query.replace("?", "").strip()
        
        # If query is too short, use original message
        if len(query) < 3:
            query = user_message
        
        return query[:100]  # Limit query length


# Global instance for easy access
_analysis_model = None

def get_analysis_model() -> AnalysisModel:
    """Get global analysis model instance"""
    global _analysis_model
    if _analysis_model is None:
        _analysis_model = AnalysisModel()
    return _analysis_model

async def analyze_for_response(
    user_message: str,
    character_name: str,
    character_personality: str,
    conversation_context: str = "",
    previous_metadata: Optional[ResponseMetadata] = None,
    memory_manager: Optional[Any] = None,
    session_id: Optional[str] = None
) -> ResponseMetadata:
    """
    Convenience function to analyze conversation state before response generation.
    This should be called BEFORE generating the main character response.
    
    Now includes memory search capability - the analysis model determines if
    memory search is needed and enriches context accordingly.
    """
    analyzer = get_analysis_model()
    
    # First, get standard analysis
    metadata = await analyzer.analyze_conversation_state(
        user_message, character_name, character_personality,
        conversation_context, previous_metadata
    )
    
    # Check if memory search is needed and we have the capability
    if memory_manager and session_id:
        memory_results = await analyzer._search_memory_if_needed(
            user_message, memory_manager, session_id
        )
        metadata.memory_context = memory_results
    
    return metadata
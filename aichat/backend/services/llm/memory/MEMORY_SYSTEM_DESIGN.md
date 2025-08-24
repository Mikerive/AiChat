# Conversation Memory System Design Document

## Overview
This document outlines the implementation of a sophisticated conversation memory system with intelligent compression, multi-user tracking, and session management for the AiChat application.

## Core Architecture

### 1. Data Models

#### Session Model
```python
class ConversationSession:
    session_id: str (UUID)
    character_id: int
    started_at: datetime
    last_activity: datetime
    participants: List[str]  # User IDs
    total_turns: int
    compression_count: int
    metadata: Dict[str, Any]
```

#### Turn Model
```python
class ConversationTurn:
    turn_id: int  # Sequential within session
    session_id: str
    speaker_id: str
    speaker_type: Literal["user", "assistant", "system"]
    message: str
    timestamp: datetime
    token_count: int
    metadata: Dict[str, Any]  # emotion, model_used, etc.
```

#### Summary Model
```python
class ConversationSummary:
    summary_id: str
    session_id: str
    summary_type: Literal["topic", "event", "fact", "emotion", "decision"]
    content: str
    turn_start: int
    turn_end: int
    participants: List[str]
    importance_score: float
    created_at: datetime
```

### 2. Compression Strategy

#### Trigger Conditions
- **Threshold**: Compress at 75% of context limit
- **Force Interval**: Compress every 100 turns regardless
- **Token Budget**: Max 8000 tokens for context window

#### Compression Configuration
```python
COMPRESSION_CONFIG = {
    "trigger_threshold": 0.75,      # 75% of context limit
    "recent_turns_keep": 10,        # Always keep last 10 turns
    "summary_max_tokens": 500,      # Summary size limit
    "preserved_turns_budget": 1000, # Tokens for important turns
    "character_reminder_tokens": 200, # Character reinforcement
    "compression_frequency": 100,    # Force compress every 100 turns
    "min_importance_score": 5.0,    # Minimum score to preserve turn
}
```

### 3. Importance Scoring Algorithm

#### Scoring Factors
```python
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
```

#### Recency Weighting
- Last 5 turns: +5 bonus
- Last 10 turns: +3 bonus
- Last 20 turns: +1 bonus

### 4. Compression Output Format

```python
class CompressedContext:
    # Character reinforcement (always first)
    character_reminder: str
    
    # Conversation summary
    session_summary: str
    key_topics: List[Tuple[str, List[int]]]  # (topic, turn_ids)
    
    # Preserved important turns
    preserved_turns: List[ConversationTurn]
    
    # Recent context (always last)
    recent_turns: List[ConversationTurn]
    
    # Metadata for reconstruction
    compression_metadata: {
        "original_turn_count": int,
        "compressed_at_turn": int,
        "compression_number": int,
        "tokens_saved": int,
        "preserved_turn_ids": List[int],
    }
```

### 5. Compression Examples

#### Example Input (20 turns, ~3000 tokens)
```
Turn 1 (User): Hi Miku! How are you today?
Turn 2 (Miku): Hello! I'm feeling energetic and ready to chat! How about you?
Turn 3 (User): I'm good! I've been learning to play guitar lately
Turn 4 (Miku): That's amazing! I love music! What songs are you learning?
Turn 5 (User): I'm trying to learn some of your songs actually
Turn 6 (Miku): [excited] Really?! That makes me so happy! Which ones?
Turn 7 (User): World is Mine and Tell Your World
Turn 8 (Miku): Those are some of my favorites! World is Mine is quite energetic!
Turn 9 (User): Yeah it's really hard though. The tempo is so fast
Turn 10 (Miku): Don't give up! Music takes practice. I had to practice a lot too!
Turn 11 (User): You practice? I thought singing came naturally to you
Turn 12 (Miku): [thoughtful] Well, I work hard to convey emotions properly in each song
Turn 13 (User): That makes sense. By the way, I'm thinking of performing at an open mic
Turn 14 (Miku): [very excited] That's wonderful! When is it?
Turn 15 (User): Next Friday at a local coffee shop
Turn 16 (Miku): I'm so proud of you for taking that step! Will you play my songs there?
Turn 17 (User): Maybe! I'm a bit nervous though
Turn 18 (Miku): [supportive] It's normal to feel nervous! But you'll do great!
Turn 19 (User): Thanks Miku. You always know what to say
Turn 20 (Miku): [warm] That's what friends are for! I believe in you!
```

#### Example Compressed Output (~500 tokens)
```python
COMPRESSED_CONTEXT = """
You are Hatsune Miku, the virtual singer. Remember: you're energetic, supportive, and passionate about music.

CONVERSATION SUMMARY:
The user is learning guitar and specifically practicing your songs "World is Mine" and "Tell Your World". They're planning to perform at an open mic next Friday at a local coffee shop. They expressed nervousness about performing, and you've been encouraging them throughout.

KEY MOMENTS:
- Turn 5-6: User revealed they're learning YOUR songs (triggered excitement)
- Turn 13-14: User announced open mic performance plan (very excited response)
- Turn 17-18: User expressed nervousness, you provided support
- Turn 19-20: Warm friendship moment established

EMOTIONAL JOURNEY:
Started energetic → Became excited about user learning your songs → Thoughtful about practice → Very excited about performance → Supportive about nervousness → Warm and friendly

IMPORTANT FACTS:
- User plays guitar (learning stage)
- Specifically learning: "World is Mine", "Tell Your World"  
- Performance: Next Friday, local coffee shop, open mic
- User is nervous about performing
- Established supportive friendship dynamic

PRESERVED TURNS:
Turn 13 (User): "That makes sense. By the way, I'm thinking of performing at an open mic"
Turn 16 (Miku): "I'm so proud of you for taking that step! Will you play my songs there?"
Turn 19 (User): "Thanks Miku. You always know what to say"
Turn 20 (Miku): "[warm] That's what friends are for! I believe in you!"

RECENT CONTEXT (Last 3 exchanges):
Turn 18 (Miku): "[supportive] It's normal to feel nervous! But you'll do great!"
Turn 19 (User): "Thanks Miku. You always know what to say"
Turn 20 (Miku): "[warm] That's what friends are for! I believe in you!"
"""
```

#### Compression Instruction Template for LLM
```python
COMPRESSION_INSTRUCTION = """
Compress this conversation following this EXACT format example:

EXAMPLE INPUT (10 turns):
User: "I lost my job today"
Assistant: "I'm so sorry to hear that"
User: "I don't know what to do"
Assistant: "Take time to process this. What field do you work in?"
User: "Software development"
Assistant: "The tech market is tough right now but your skills are valuable"
User: "I have a family to support"
Assistant: "That pressure is real. Have you looked at your emergency savings?"
User: "We have 3 months saved"
Assistant: "That's a good buffer. You can be strategic about your next move"

EXAMPLE OUTPUT:
SUMMARY: User lost their software development job and is worried about supporting family. Has 3 months emergency savings.
KEY MOMENTS: Turn 1 (job loss revealed), Turn 7 (family pressure mentioned), Turn 9 (savings confirmed)
EMOTIONAL: Distressed → Worried → Slightly relieved
FACTS: Unemployed software developer, has family, 3 months savings
DECISIONS: Will be strategic about job search

Now compress the following conversation using THE SAME FORMAT:
{conversation_to_compress}
"""
```

### 6. Character Reinforcement Template

```python
CHARACTER_REINFORCEMENT_TEMPLATE = """
You are {name}. As a reminder of your core identity:

PERSONALITY: {personality}
BACKGROUND: {profile}

CONVERSATION CONTEXT:
- We've been talking for {turn_count} exchanges
- Main topics discussed: {topics}
- Your emotional journey: {emotional_arc}
- Key decisions made: {decisions}

BEHAVIORAL NOTES:
- Maintain your established traits: {observed_traits}
- Current emotional state: {current_emotion}
- Relationship dynamic: {relationship_notes}

Continue responding as {name} with these characteristics in mind.
"""
```

### 6. Database Schema

```sql
-- Sessions table
CREATE TABLE conversation_sessions (
    session_id TEXT PRIMARY KEY,
    character_id INTEGER NOT NULL,
    started_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL,
    participants JSON NOT NULL,
    total_turns INTEGER DEFAULT 0,
    compression_count INTEGER DEFAULT 0,
    metadata JSON,
    FOREIGN KEY (character_id) REFERENCES characters(id)
);

-- Conversation turns table
CREATE TABLE conversation_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    speaker_id TEXT NOT NULL,
    speaker_type TEXT NOT NULL CHECK(speaker_type IN ('user', 'assistant', 'system')),
    message TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    token_count INTEGER,
    metadata JSON,
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id),
    UNIQUE(session_id, turn_number)
);

-- Summaries table
CREATE TABLE conversation_summaries (
    summary_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    summary_type TEXT NOT NULL,
    content TEXT NOT NULL,
    turn_start INTEGER NOT NULL,
    turn_end INTEGER NOT NULL,
    participants JSON NOT NULL,
    importance_score REAL NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id)
);

-- Compression events table
CREATE TABLE compression_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    compressed_at_turn INTEGER NOT NULL,
    original_token_count INTEGER NOT NULL,
    compressed_token_count INTEGER NOT NULL,
    preserved_turns JSON NOT NULL,
    summary TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id)
);

-- Indexes for performance
CREATE INDEX idx_turns_session ON conversation_turns(session_id);
CREATE INDEX idx_turns_speaker ON conversation_turns(speaker_id);
CREATE INDEX idx_summaries_session ON conversation_summaries(session_id);
CREATE INDEX idx_summaries_type ON conversation_summaries(summary_type);
CREATE INDEX idx_compression_session ON compression_events(session_id);
```

### 7. Implementation Classes

#### MemoryManager
```python
class MemoryManager:
    """Central manager for conversation memory"""
    
    async def start_session(character_id: int, user_id: str) -> ConversationSession
    async def add_turn(session_id: str, speaker: str, message: str, metadata: Dict)
    async def get_session_context(session_id: str) -> CompressedContext
    async def compress_if_needed(session_id: str) -> Optional[CompressedContext]
    async def search_memories(query: str, session_id: Optional[str]) -> List[ConversationTurn]
```

#### CompressionEngine
```python
class CompressionEngine:
    """Handles intelligent conversation compression"""
    
    async def compress(session: ConversationSession, turns: List[ConversationTurn]) -> CompressedContext
    async def score_importance(turn: ConversationTurn) -> float
    async def generate_summary(turns: List[ConversationTurn]) -> str
    async def extract_key_moments(turns: List[ConversationTurn]) -> List[Tuple[str, List[int]]]
    async def reinforce_character(character: Character, context: Dict) -> str
```

#### ImportanceScorer
```python
class ImportanceScorer:
    """Scores conversation turns for preservation priority"""
    
    def score_turn(turn: ConversationTurn) -> float
    def detect_emotion_peak(turn: ConversationTurn) -> bool
    def detect_decision(turn: ConversationTurn) -> bool
    def detect_topic_change(turn: ConversationTurn, previous: ConversationTurn) -> bool
    def extract_user_info(turn: ConversationTurn) -> Optional[Dict]
```

### 8. API Endpoints

```python
# New memory-aware endpoints
POST   /api/sessions/start          # Start new conversation session
GET    /api/sessions/{id}/context   # Get current compressed context
POST   /api/sessions/{id}/compress  # Force compression
GET    /api/sessions/{id}/history   # Get full conversation history
GET    /api/sessions/{id}/summary   # Get conversation summary
POST   /api/memory/search           # Search across all memories
```

### 9. Integration Points

#### Chat Service Integration
```python
class ChatService:
    async def process_message(message: str, session_id: str):
        # 1. Add user turn to memory
        await memory_manager.add_turn(session_id, user_id, message, {...})
        
        # 2. Check if compression needed
        context = await memory_manager.compress_if_needed(session_id)
        
        # 3. Generate response with context
        response = await llm_service.generate(message, context)
        
        # 4. Add assistant turn to memory
        await memory_manager.add_turn(session_id, character_id, response, {...})
        
        return response
```

### 10. Implementation Phases

#### Phase 1: Core Memory System (Week 1)
- [ ] Create database schema
- [ ] Implement ConversationSession model
- [ ] Implement ConversationTurn model
- [ ] Basic session management

#### Phase 2: Compression Engine (Week 2)
- [ ] Implement ImportanceScorer
- [ ] Create compression algorithm
- [ ] Character reinforcement system
- [ ] Summary generation

#### Phase 3: Storage & Retrieval (Week 3)
- [ ] Database operations
- [ ] Search functionality
- [ ] Context reconstruction
- [ ] API endpoints

#### Phase 4: Integration (Week 4)
- [ ] Integrate with ChatService
- [ ] Update LLM services
- [ ] WebSocket notifications
- [ ] Testing & optimization

### 11. Configuration

```python
# config/memory_config.py
MEMORY_CONFIG = {
    "context_window_size": 8000,
    "compression_threshold": 0.75,
    "max_session_duration_hours": 24,
    "max_turns_per_session": 1000,
    "summary_model": "openrouter-gpt-mini",  # Cheap model for summaries
    "importance_threshold": 5.0,
    "enable_auto_compression": True,
    "enable_cross_session_memory": False,  # Future feature
}
```

### 12. Success Metrics

- **Memory Efficiency**: <50% token usage after compression
- **Context Quality**: >90% important information preserved
- **Character Consistency**: No personality drift over 100+ turns
- **Response Time**: <100ms compression overhead
- **Cost Reduction**: 60% reduction in API costs for long conversations

## Notes

- All timestamps in UTC
- Token counting uses tiktoken for accuracy
- Summaries generated with cheap models to save costs
- Full history always preserved in database
- Compression is transparent to end user
- System can reconstruct context from any point
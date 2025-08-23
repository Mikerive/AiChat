"""
Pydantic schemas for API models
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, HttpUrl, validator


class Character(BaseModel):
    """Character schema"""

    id: Optional[int] = None
    name: str
    profile: str
    personality: str
    avatar_url: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message schema"""

    text: str
    character: str

    @validator("text")
    def text_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("text must not be empty")
        return v


class ChatResponse(BaseModel):
    """Chat response schema"""

    user_input: str
    response: str
    character: str
    emotion: Optional[str] = None
    model_used: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.now()
        super().__init__(**data)


class CharacterSwitch(BaseModel):
    """Character switch schema"""

    character: str


class SwitchCharacterRequest(BaseModel):
    """Switch character request schema"""

    character: str

    @validator("character")
    def character_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("character must not be empty")
        return v


class CharacterResponse(BaseModel):
    """Character response schema"""

    user_input: str
    character: str
    character_name: str
    response: str
    emotion: Optional[str] = None
    model_used: Optional[str] = None


class TTSRequest(BaseModel):
    """Text-to-speech request schema with emotional tone control"""

    text: str
    character: str = "hatsune_miku"
    speed: float = 1.0
    pitch: float = 1.0
    emotion: Optional[str] = None
    emotion_intensity: Optional[float] = None
    voice_preset: Optional[str] = None
    auto_emotion_sync: bool = True

    @validator("speed", "pitch")
    def speed_pitch_must_be_valid(cls, v):
        if v <= 0.5 or v >= 2.0:
            raise ValueError("speed and pitch must be between 0.5 and 2.0")
        return v
    
    @validator("emotion_intensity")
    def emotion_intensity_must_be_valid(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("emotion_intensity must be between 0.0 and 1.0")
        return v


class TTSResponse(BaseModel):
    """Text-to-speech response schema with emotional tone information"""

    audio_file: str
    audio_format: str
    character: str
    text: str
    duration: Optional[float] = None
    emotion_used: Optional[str] = None
    voice_settings: Optional[Dict[str, float]] = None
    preset_used: Optional[str] = None


class STTResponse(BaseModel):
    """Speech-to-text response schema"""

    text: str
    language: str
    confidence: float
    processing_time: Optional[float] = None

    @validator("confidence")
    def confidence_must_be_valid(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class WhisperResponse(BaseModel):
    """Whisper transcription response schema"""

    text: str
    language: str
    confidence: float
    processing_time: float


class TrainingProgress(BaseModel):
    """Training progress schema"""

    epoch: int
    total_epochs: int
    progress: float
    loss: float


class ModelInfo(BaseModel):
    """Voice model information schema"""

    id: Optional[int] = None
    name: str
    model_path: str
    character_id: Optional[int] = None
    status: str
    epochs_trained: Optional[int] = None
    loss: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TrainingDataInfo(BaseModel):
    """Training data information schema"""

    id: Optional[int] = None
    filename: str
    transcript: Optional[str] = None
    duration: Optional[float] = None
    speaker: str
    emotion: Optional[str] = None
    quality: Optional[str] = None
    created_at: Optional[str] = None


class VoiceProcessingRequest(BaseModel):
    """Voice processing request schema"""

    character: str
    session_id: Optional[str] = None


class VoiceProcessingResponse(BaseModel):
    """Voice processing response schema"""

    transcription: Dict[str, Any]
    chat_response: Dict[str, Any]
    audio_file: str


class WebhookRequest(BaseModel):
    """Webhook request schema"""

    url: HttpUrl

    @validator("url")
    def url_must_be_http_or_https(cls, v):
        if not str(v).startswith(("http://", "https://")):
            raise ValueError("url must use http or https protocol")
        return v


class SystemStatus(BaseModel):
    """System status schema"""

    status: str
    timestamp: Optional[str] = None
    uptime: float
    cpu_usage: Optional[float] = None
    memory_usage: Dict[str, Any]
    disk_usage: Optional[dict] = None
    services: Dict[str, str]

    @validator("status")
    def status_must_be_valid(cls, v):
        valid_statuses = ["running", "stopped", "error", "starting", "stopping"]
        if v not in valid_statuses:
            raise ValueError(f"status must be one of: {valid_statuses}")
        return v


class HealthCheck(BaseModel):
    """Health check schema"""

    status: str
    timestamp: str
    checks: dict
    metrics: dict


class SystemMetrics(BaseModel):
    """System metrics schema"""

    cpu: dict
    memory: dict
    disk: dict
    network: dict
    system: dict


class SystemConfig(BaseModel):
    """System configuration schema"""

    api: dict
    database: dict
    audio: dict
    logging: dict
    models: dict


class EventLog(BaseModel):
    """Event log schema"""

    id: str
    event_type: str
    message: str
    data: dict
    timestamp: str
    severity: str
    source: str


class ChatHistory(BaseModel):
    """Chat history schema"""

    history: List[dict]


class VoiceClips(BaseModel):
    """Voice clips schema"""

    clips: List[TrainingDataInfo]


class VoiceModels(BaseModel):
    """Voice models schema"""

    models: List[ModelInfo]


class Checkpoints(BaseModel):
    """Checkpoints schema"""

    checkpoints: dict


class UploadResponse(BaseModel):
    """Upload response schema"""

    status: str
    filename: str
    path: str


class ProcessResponse(BaseModel):
    """Process response schema"""

    status: str
    clips_created: List[str]
    database_entries: int


class TrainResponse(BaseModel):
    """Train response schema"""

    status: str
    model_name: str
    output_dir: str
    epochs: int
    batch_size: int


class TranscriptionResponse(BaseModel):
    """Transcription response schema"""

    id: Optional[int] = None
    filename: str
    transcript: str
    language: str
    confidence: float
    duration: Optional[float] = None
    training_data_id: Optional[int] = None


class WebSocketMessage(BaseModel):
    """WebSocket message schema"""

    type: str
    event: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict] = None
    timestamp: Optional[str] = None


class WebSocketSubscription(BaseModel):
    """WebSocket subscription schema"""

    type: str = "subscribe"
    events: List[str]


class WebSocketChat(BaseModel):
    """WebSocket chat message schema"""

    type: str = "chat"
    text: str
    character: str = "hatsune_miku"


class WebSocketPing(BaseModel):
    """WebSocket ping schema"""

    type: str = "ping"


class WebSocketStatusRequest(BaseModel):
    """WebSocket status request schema"""

    type: str = "get_status"


class WebSocketError(BaseModel):
    """WebSocket error schema"""

    type: str = "error"
    message: str
    timestamp: str


# PydanticAI and Enhanced LLM Schemas


class LLMProvider(str, Enum):
    """Available LLM providers"""

    PYDANTIC_AI = "pydantic_ai"
    OPENROUTER = "openrouter"
    AUTO = "auto"


class EmotionState(BaseModel):
    """Character emotion state"""

    emotion: str
    intensity: float
    context: str

    @validator("intensity")
    def intensity_must_be_valid(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError("intensity must be between 0.0 and 1.0")
        return v


class VoiceSettings(BaseModel):
    """Voice generation settings for TTS"""

    speed: float = 1.0
    pitch: float = 1.0
    voice_model: str = "default"

    @validator("speed", "pitch")
    def speed_pitch_must_be_valid(cls, v):
        if v < 0.5 or v > 2.0:
            raise ValueError("speed and pitch must be between 0.5 and 2.0")
        return v


class ConversationMemory(BaseModel):
    """Conversation memory entry"""

    topic: str
    details: str
    timestamp: str
    importance: float = 0.5

    @validator("importance")
    def importance_must_be_valid(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError("importance must be between 0.0 and 1.0")
        return v


class EnhancedChatRequest(BaseModel):
    """Enhanced chat request with PydanticAI features"""

    text: str
    character: str
    provider: LLMProvider = LLMProvider.AUTO
    model: Optional[str] = None
    use_tools: bool = True
    use_memory: bool = True
    temperature: float = 0.7
    max_tokens: int = 1000

    @validator("text")
    def text_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("text must not be empty")
        return v

    @validator("temperature")
    def temperature_must_be_valid(cls, v):
        if v < 0.0 or v > 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v


class EnhancedChatResponse(BaseModel):
    """Enhanced chat response with PydanticAI features"""

    user_input: str
    response: str
    character: str
    emotion: Optional[str] = None
    emotion_state: Optional[EmotionState] = None
    voice_settings: Optional[VoiceSettings] = None
    model_used: Optional[str] = None
    provider_used: Optional[str] = None
    conversation_history: List[ConversationMemory] = []
    tools_used: List[str] = []
    timestamp: Optional[datetime] = None
    success: bool = True

    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.now()
        super().__init__(**data)


class StreamingChatChunk(BaseModel):
    """Streaming chat response chunk"""

    content: str
    character: str
    emotion: Optional[str] = None
    provider_used: Optional[str] = None
    final: bool = False
    timestamp: Optional[str] = None


class LLMProviderStatus(BaseModel):
    """LLM provider status information"""

    name: str
    available: bool
    models: List[str] = []
    features: List[str] = []
    error: Optional[str] = None
    api_key_configured: Optional[bool] = None


class SystemLLMStatus(BaseModel):
    """Overall LLM system status"""

    providers: Dict[str, LLMProviderStatus]
    default_provider: Optional[str] = None
    total_models: int
    features_available: List[str] = []


class ToolCall(BaseModel):
    """Function tool call information"""

    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[str] = None
    success: bool = True
    timestamp: Optional[str] = None


class EnhancedWebSocketMessage(BaseModel):
    """Enhanced WebSocket message with LLM features"""

    type: str
    event: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict] = None
    emotion_state: Optional[EmotionState] = None
    voice_settings: Optional[VoiceSettings] = None
    provider_used: Optional[str] = None
    streaming: bool = False
    timestamp: Optional[str] = None


class MemoryQuery(BaseModel):
    """Memory query request"""

    character: str
    query: Optional[str] = None
    limit: int = 10

    @validator("limit")
    def limit_must_be_valid(cls, v):
        if v < 1 or v > 100:
            raise ValueError("limit must be between 1 and 100")
        return v


class MemoryResponse(BaseModel):
    """Memory query response"""

    character: str
    memories: List[ConversationMemory]
    total_count: int


# Enhanced Emotional Control Schemas

class EmotionAnalysisRequest(BaseModel):
    """Request for emotion analysis"""
    
    text: str
    character: Optional[str] = None
    
    @validator("text")
    def text_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("text must not be empty")
        return v


class EmotionAnalysisResponse(BaseModel):
    """Response from emotion analysis"""
    
    detected_emotion: str
    intensity: float
    reasoning: str
    confidence: float
    alternative_emotions: List[Dict[str, float]] = []
    
    @validator("intensity", "confidence")
    def values_must_be_valid(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError("intensity and confidence must be between 0.0 and 1.0")
        return v


class VoicePresetRequest(BaseModel):
    """Request to apply voice preset"""
    
    character: str
    preset_name: str
    
    @validator("preset_name")
    def preset_name_must_be_valid(cls, v):
        valid_presets = ["cheerful", "melancholy", "energetic", "calm", "dramatic", "whispery", "confident", "shy"]
        if v.lower() not in valid_presets:
            raise ValueError(f"preset_name must be one of: {', '.join(valid_presets)}")
        return v.lower()


class VoicePresetResponse(BaseModel):
    """Response from voice preset application"""
    
    character: str
    preset_applied: str
    voice_settings: VoiceSettings
    description: str


class EmotionalTTSRequest(BaseModel):
    """Enhanced TTS request with emotional intelligence"""
    
    text: str
    character: str = "hatsune_miku"
    auto_detect_emotion: bool = True
    manual_emotion: Optional[str] = None
    manual_intensity: Optional[float] = None
    voice_preset: Optional[str] = None
    speed_override: Optional[float] = None
    pitch_override: Optional[float] = None
    
    @validator("manual_intensity")
    def intensity_must_be_valid(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("manual_intensity must be between 0.0 and 1.0")
        return v
    
    @validator("speed_override", "pitch_override")
    def overrides_must_be_valid(cls, v):
        if v is not None and (v < 0.5 or v > 2.0):
            raise ValueError("speed and pitch overrides must be between 0.5 and 2.0")
        return v


class EmotionalTTSResponse(BaseModel):
    """Enhanced TTS response with emotional information"""
    
    audio_file: str
    audio_format: str
    character: str
    text: str
    duration: Optional[float] = None
    emotion_detected: Optional[str] = None
    emotion_intensity: Optional[float] = None
    emotion_reasoning: Optional[str] = None
    voice_settings_used: VoiceSettings
    preset_used: Optional[str] = None
    auto_adjustments_made: bool = False


class CharacterPersonalityUpdate(BaseModel):
    """Request to update character personality traits"""
    
    character: str
    new_personality: str
    add_traits: List[str] = []
    remove_traits: List[str] = []
    
    @validator("new_personality")
    def personality_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("new_personality must not be empty")
        return v


class ToolUsageStats(BaseModel):
    """Statistics about tool usage in conversations"""
    
    character: str
    session_id: Optional[str] = None
    tools_used: Dict[str, int] = {}
    total_tool_calls: int = 0
    emotion_changes: int = 0
    voice_adjustments: int = 0
    memory_operations: int = 0
    character_actions: int = 0


class ConversationAnalysis(BaseModel):
    """Analysis of conversation patterns and emotional flow"""
    
    character: str
    total_messages: int
    dominant_emotions: List[Dict[str, Any]] = []
    emotion_transitions: List[Dict[str, Any]] = []
    voice_setting_changes: List[Dict[str, Any]] = []
    memory_growth: Dict[str, int] = {}
    tool_effectiveness: Dict[str, float] = {}
    conversation_sentiment: str = "neutral"
    engagement_score: float = 0.5
    
    @validator("engagement_score")
    def engagement_must_be_valid(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError("engagement_score must be between 0.0 and 1.0")
        return v


# Additional Response Models for API Endpoints

class CharacterSwitchResponse(BaseModel):
    """Character switch operation response"""
    
    character: str
    character_name: str
    greeting: str
    status: str


class AudioDeviceInfo(BaseModel):
    """Audio device information"""
    
    id: int
    name: str
    channels: int
    sample_rate: int
    is_default: bool


class AudioDevicesResponse(BaseModel):
    """Audio devices list response"""
    
    input_devices: List[AudioDeviceInfo]
    output_devices: List[AudioDeviceInfo]


class AudioDeviceSetResponse(BaseModel):
    """Audio device set operation response"""
    
    status: str
    device_id: int


class AudioRecordResponse(BaseModel):
    """Audio recording response"""
    
    status: str
    audio_path: str
    duration: float
    file_size: int
    audio_info: Dict[str, Any]


class AudioPlayResponse(BaseModel):
    """Audio playback response"""
    
    status: str
    audio_path: str


class AudioVolumeResponse(BaseModel):
    """Audio volume set response"""
    
    status: str
    volume: float


class AudioInfoResponse(BaseModel):
    """Audio file information response"""
    
    status: str
    audio_info: Dict[str, Any]


class AudioIOStatusResponse(BaseModel):
    """Audio IO service status response"""
    
    status: str
    audio_io: Dict[str, Any]


class RecordTranscribeResponse(BaseModel):
    """Record and transcribe response"""
    
    status: str
    transcription: Dict[str, Any]


class JobCheckpointResponse(BaseModel):
    """Training job checkpoint response"""
    
    job_id: str
    checkpoint: Dict[str, Any]


class JobLogsResponse(BaseModel):
    """Training job logs response"""
    
    job_id: str
    log_file: str
    tail: str


class SystemStatusResponse(BaseModel):
    """System status response"""
    
    backend: str
    chat_service: str
    current_character: Dict[str, Optional[str]]
    models: Dict[str, str]


class WebhookListResponse(BaseModel):
    """Webhook list response"""
    
    webhooks: List[str]


class WebhookOperationResponse(BaseModel):
    """Webhook operation response"""
    
    status: str
    message: str


class TestEventResponse(BaseModel):
    """Test event emission response"""
    
    status: str
    message: str


class SileroVADResponse(BaseModel):
    """Silero VAD test response"""
    
    session: Dict[str, Any]
    silero: Dict[str, Any]


class ChatHistoryResponse(BaseModel):
    """Chat history response"""
    
    history: List[Dict[str, Any]]


class ChatterboxStatusResponse(BaseModel):
    """Chatterbox TTS service status response"""
    
    service: str
    device: str
    device_info: Dict[str, Any]
    model_loaded: bool
    default_voice: str
    supports_streaming: bool
    punctuation_pauses: Dict[str, float]
    status: str
    audio_io: Dict[str, Any]
    cpu_fallback: bool
    performance_mode: str


class IntensityStreamingResponse(BaseModel):
    """Intensity-first streaming response"""
    
    character: str
    total_chunks: int
    exaggeration_used: float
    intensity_description: str
    audio_segments: List[Dict[str, Any]]
    processing_time: float
    device_info: Dict[str, Any]

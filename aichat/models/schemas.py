"""
Pydantic schemas for API models
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

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
    """Text-to-speech request schema"""

    text: str
    character: str = "hatsune_miku"
    speed: float = 1.0

    @validator("speed")
    def speed_must_be_valid(cls, v):
        if v <= 0.0 or v >= 3.0:
            raise ValueError("speed must be between 0.0 and 3.0")
        return v


class TTSResponse(BaseModel):
    """Text-to-speech response schema"""

    audio_file: str
    audio_format: str
    character: str
    text: str
    duration: Optional[float] = None


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

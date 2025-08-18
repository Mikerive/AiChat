"""
Pydantic schemas for API models
"""

from typing import Optional, List
from pydantic import BaseModel


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
    character: str = "hatsune_miku"


class CharacterSwitch(BaseModel):
    """Character switch schema"""
    character: str


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


class SystemStatus(BaseModel):
    """System status schema"""
    status: str
    timestamp: str
    uptime: float
    cpu_usage: float
    memory_usage: float
    disk_usage: dict
    services: dict


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
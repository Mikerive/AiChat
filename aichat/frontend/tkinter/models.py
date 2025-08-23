"""
GUI Models for chat messages and interface objects
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, Literal
from enum import Enum


class MessageType(Enum):
    """Message type enumeration"""
    USER = "user"
    AI = "ai" 
    SYSTEM = "system"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    VOICE = "voice"


class MessageAlignment(Enum):
    """Message alignment enumeration"""
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


@dataclass
class ChatMessage:
    """Enhanced chat message object with styling and alignment"""
    
    # Core message data
    sender: str
    content: str
    message_type: MessageType
    timestamp: datetime
    
    # Optional metadata
    metadata: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None  # For voice transcription
    emotion: Optional[str] = None       # For AI responses
    model_used: Optional[str] = None    # For AI responses
    
    # Display properties
    alignment: Optional[MessageAlignment] = None
    max_width: int = 80  # Character wrap width
    
    def __post_init__(self):
        """Set default alignment based on message type"""
        if self.alignment is None:
            self.alignment = self._get_default_alignment()
    
    def _get_default_alignment(self) -> MessageAlignment:
        """Get default alignment based on message type"""
        if self.message_type in [MessageType.USER, MessageType.VOICE]:
            return MessageAlignment.LEFT
        elif self.message_type == MessageType.AI:
            return MessageAlignment.RIGHT
        else:  # System, info, success, warning, error
            return MessageAlignment.CENTER
    
    @property
    def display_sender(self) -> str:
        """Get formatted sender name for display"""
        if self.message_type == MessageType.VOICE:
            confidence_str = ""
            if self.confidence and self.confidence < 0.8:
                confidence_str = f" ({self.confidence:.0%})"
            return f"{self.sender} (Voice){confidence_str}"
        return self.sender
    
    @property
    def sender_tag(self) -> str:
        """Get tag name for sender styling"""
        return f"{self.message_type.value}_sender"
    
    @property
    def message_tag(self) -> str:
        """Get tag name for message content styling"""
        return f"{self.message_type.value}_message"
    
    @property
    def timestamp_str(self) -> str:
        """Get formatted timestamp string"""
        return self.timestamp.strftime("%H:%M:%S")
    
    @property
    def is_left_aligned(self) -> bool:
        """Check if message should be left aligned"""
        return self.alignment == MessageAlignment.LEFT
    
    @property
    def is_right_aligned(self) -> bool:
        """Check if message should be right aligned"""
        return self.alignment == MessageAlignment.RIGHT
    
    @property
    def is_center_aligned(self) -> bool:
        """Check if message should be center aligned"""
        return self.alignment == MessageAlignment.CENTER
    
    def wrap_content(self, width: Optional[int] = None) -> list[str]:
        """Wrap message content to specified width"""
        import textwrap
        wrap_width = width or self.max_width
        return textwrap.wrap(self.content, width=wrap_width)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'sender': self.sender,
            'content': self.content,
            'message_type': self.message_type.value,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'confidence': self.confidence,
            'emotion': self.emotion,
            'model_used': self.model_used,
            'alignment': self.alignment.value if self.alignment else None,
            'max_width': self.max_width
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create from dictionary"""
        return cls(
            sender=data['sender'],
            content=data['content'],
            message_type=MessageType(data['message_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata'),
            confidence=data.get('confidence'),
            emotion=data.get('emotion'),
            model_used=data.get('model_used'),
            alignment=MessageAlignment(data['alignment']) if data.get('alignment') else None,
            max_width=data.get('max_width', 80)
        )
    
    @classmethod
    def create_user_message(cls, content: str, sender: str = "You") -> 'ChatMessage':
        """Create a user message"""
        return cls(
            sender=sender,
            content=content,
            message_type=MessageType.USER,
            timestamp=datetime.now()
        )
    
    @classmethod
    def create_ai_message(cls, content: str, sender: str = "AI", 
                         emotion: Optional[str] = None, 
                         model_used: Optional[str] = None) -> 'ChatMessage':
        """Create an AI message"""
        return cls(
            sender=sender,
            content=content,
            message_type=MessageType.AI,
            timestamp=datetime.now(),
            emotion=emotion,
            model_used=model_used
        )
    
    @classmethod
    def create_voice_message(cls, content: str, confidence: Optional[float] = None,
                            sender: str = "You") -> 'ChatMessage':
        """Create a voice transcription message"""
        return cls(
            sender=sender,
            content=content,
            message_type=MessageType.VOICE,
            timestamp=datetime.now(),
            confidence=confidence
        )
    
    @classmethod
    def create_system_message(cls, content: str, msg_type: MessageType = MessageType.SYSTEM,
                             sender: str = "System") -> 'ChatMessage':
        """Create a system message"""
        return cls(
            sender=sender,
            content=content,
            message_type=msg_type,
            timestamp=datetime.now()
        )


@dataclass
class ChatDisplayConfig:
    """Configuration for chat display formatting"""
    
    # Layout settings
    message_spacing: int = 10       # Vertical space between messages
    indent_size: int = 20           # Pixels to indent for alignment
    max_message_width: int = 400    # Max pixel width for messages
    
    # User message settings (left-aligned)
    user_indent_left: int = 20      # Left margin for user messages
    user_indent_right: int = 100    # Right margin for user messages
    
    # AI message settings (right-aligned)  
    ai_indent_left: int = 100       # Left margin for AI messages
    ai_indent_right: int = 20       # Right margin for AI messages
    
    # Center message settings
    center_indent: int = 50         # Side margins for center messages
    
    # Visual styling
    show_timestamps: bool = True
    show_sender_names: bool = True
    wrap_long_messages: bool = True
    bubble_style: bool = True       # Show messages in bubble-like format


@dataclass
class CharacterProfile:
    """Character profile model for AI characters"""
    
    # Core character data
    id: str
    name: str
    description: Optional[str] = None
    voice_model: Optional[str] = None
    
    # Character settings
    personality: Optional[str] = None
    language: str = "en"
    is_active: bool = False
    
    # Voice settings
    voice_speed: float = 1.0
    voice_pitch: float = 1.0
    voice_emotion: Optional[str] = None
    
    # Model/AI settings
    model_name: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 150
    system_prompt: Optional[str] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    avatar_path: Optional[str] = None
    tags: Optional[list[str]] = None
    
    def __post_init__(self):
        """Set default values after initialization"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.tags is None:
            self.tags = []
    
    @property
    def display_name(self) -> str:
        """Get formatted name for display"""
        if self.is_active:
            return f"● {self.name}"
        return f"○ {self.name}"
    
    @property
    def short_description(self) -> str:
        """Get shortened description for UI display"""
        if not self.description:
            return "No description"
        return self.description[:100] + "..." if len(self.description) > 100 else self.description
    
    @property
    def voice_settings(self) -> Dict[str, Any]:
        """Get voice generation settings"""
        return {
            'voice_model': self.voice_model or 'default',
            'speed': self.voice_speed,
            'pitch': self.voice_pitch,
            'emotion': self.voice_emotion
        }
    
    @property
    def ai_settings(self) -> Dict[str, Any]:
        """Get AI model settings"""
        return {
            'model_name': self.model_name or 'default',
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'system_prompt': self.system_prompt
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'voice_model': self.voice_model,
            'personality': self.personality,
            'language': self.language,
            'is_active': self.is_active,
            'voice_speed': self.voice_speed,
            'voice_pitch': self.voice_pitch,
            'voice_emotion': self.voice_emotion,
            'model_name': self.model_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'system_prompt': self.system_prompt,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'avatar_path': self.avatar_path,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterProfile':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description'),
            voice_model=data.get('voice_model'),
            personality=data.get('personality'),
            language=data.get('language', 'en'),
            is_active=data.get('is_active', False),
            voice_speed=data.get('voice_speed', 1.0),
            voice_pitch=data.get('voice_pitch', 1.0),
            voice_emotion=data.get('voice_emotion'),
            model_name=data.get('model_name'),
            temperature=data.get('temperature', 0.7),
            max_tokens=data.get('max_tokens', 150),
            system_prompt=data.get('system_prompt'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            avatar_path=data.get('avatar_path'),
            tags=data.get('tags', [])
        )
    
    @classmethod
    def create_default_character(cls, name: str) -> 'CharacterProfile':
        """Create a default character profile"""
        return cls(
            id=name.lower().replace(' ', '_'),
            name=name,
            description=f"Default AI character: {name}",
            voice_model='default'
        )
    
    def update_activity_timestamp(self):
        """Update the last activity timestamp"""
        self.updated_at = datetime.now()
    
    def clone(self, new_name: str, new_id: Optional[str] = None) -> 'CharacterProfile':
        """Create a copy of this character with a new name"""
        clone_id = new_id or new_name.lower().replace(' ', '_')
        
        return CharacterProfile(
            id=clone_id,
            name=new_name,
            description=self.description,
            voice_model=self.voice_model,
            personality=self.personality,
            language=self.language,
            is_active=False,  # Clone is not active by default
            voice_speed=self.voice_speed,
            voice_pitch=self.voice_pitch,
            voice_emotion=self.voice_emotion,
            model_name=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            system_prompt=self.system_prompt,
            avatar_path=self.avatar_path,
            tags=self.tags.copy() if self.tags else []
        )
"""
Event system for real-time communication and monitoring
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Awaitable
from pathlib import Path

from database import EventLog as EventLogModel
from database import db_ops

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for the system"""
    # System events
    SYSTEM_STATUS = "system.status"
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"
    ERROR_OCCURRED = "error.occurred"
    
    # Chat events
    CHAT_MESSAGE = "chat.message"
    CHAT_RESPONSE = "chat.response"
    CHARACTER_SWITCHED = "character.switched"
    
    # Voice events
    AUDIO_TRANSCRIBED = "audio.transcribed"
    AUDIO_GENERATED = "audio.generated"
    AUDIO_PROCESSED = "audio.processed"
    AUDIO_UPLOADED = "audio.uploaded"
    AUDIO_CAPTURED = "audio.captured"
    
    # Training events
    TRAINING_STARTED = "training.started"
    TRAINING_PROGRESS = "training.progress"
    TRAINING_COMPLETED = "training.completed"
    TRAINING_FAILED = "training.failed"
    
    # Model events
    MODEL_LOADED = "model.loaded"
    MODEL_FAILED = "model.failed"
    MODEL_CHANGED = "model.changed"
    
    # WebSocket events
    WEBSOCKET_CONNECTED = "websocket.connected"
    WEBSOCKET_DISCONNECTED = "websocket.disconnected"


class EventSeverity(Enum):
    """Event severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Event:
    """Event data structure"""
    
    def __init__(self, event_type: EventType, message: str, data: Optional[Dict[str, Any]] = None,
                 severity: EventSeverity = EventSeverity.INFO, source: Optional[str] = None):
        self.event_type = event_type
        self.message = message
        self.data = data or {}
        self.severity = severity
        self.source = source
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "id": id(self),
            "event_type": self.event_type.value,
            "message": self.message,
            "data": self.data,
            "severity": self.severity.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict())


class EventSystem:
    """Event system for handling real-time communication"""
    
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.global_subscribers: List[Callable] = []
        self.websocket_connections: List[Any] = []
        self.event_log: List[Event] = []
        self.max_log_size = 1000
        self._initialized = False
    
    async def initialize(self):
        """Initialize the event system and persistent event sink"""
        try:
            self._initialized = True
            logger.info("Event system initialized")
            
            # Ensure disk log directory exists for durable event logging
            try:
                logs_dir = Path("backend/tts_finetune_app/logs")
                logs_dir.mkdir(parents=True, exist_ok=True)
                self.events_log_path = logs_dir / "events.log"
            except Exception as _e:
                # If we cannot create the log directory, continue without disk sink
                logger.warning(f"Could not create event logs directory: {_e}")
                self.events_log_path = None

            # Subscribe a persistent disk-writer to all events (best-effort)
            async def _write_event_to_disk(event):
                try:
                    if not getattr(self, "events_log_path", None):
                        return
                    # Append event JSON to the events log file
                    with open(self.events_log_path, "a", encoding="utf-8") as f:
                        f.write(event.to_json() + "\n")
                except Exception as _e:
                    logger.debug(f"Failed to write event to disk: {_e}")

            # Register the disk writer as a global subscriber
            try:
                await self.subscribe_to_all(_write_event_to_disk)
            except Exception as _e:
                logger.debug(f"Failed to subscribe disk-writer: {_e}")
            
            # Emit initialization event
            await self.emit(EventType.SERVICE_STARTED, "Event system initialized")
            
        except Exception as e:
            logger.error(f"Error initializing event system: {e}")
            raise
    
    async def emit(self, event_type: EventType, message: str, data: Optional[Dict[str, Any]] = None,
                  severity: EventSeverity = EventSeverity.INFO, source: Optional[str] = None):
        """Emit an event"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Create event
            event = Event(event_type, message, data, severity, source)
            
            # Log event
            await self._log_event(event)
            
            # Notify subscribers
            await self._notify_subscribers(event)
            
            # Log for debugging
            logger.debug(f"Event emitted: {event_type.value} - {message}")
            
        except Exception as e:
            logger.error(f"Error emitting event: {e}")
    
    async def subscribe(self, event_type: EventType, callback: Callable[[Event], Awaitable[None]]):
        """Subscribe to specific event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to event: {event_type.value}")
    
    async def subscribe_to_all(self, callback: Callable[[Event], Awaitable[None]]):
        """Subscribe to all events"""
        self.global_subscribers.append(callback)
        logger.debug("Subscribed to all events")
    
    async def unsubscribe(self, event_type: EventType, callback: Callable[[Event], Awaitable[None]]):
        """Unsubscribe from specific event type"""
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from event: {event_type.value}")
            except ValueError:
                pass
    
    async def unsubscribe_from_all(self, callback: Callable[[Event], Awaitable[None]]):
        """Unsubscribe from all events"""
        if callback in self.global_subscribers:
            self.global_subscribers.remove(callback)
            logger.debug("Unsubscribed from all events")
    
    async def _notify_subscribers(self, event: Event):
        """Notify all subscribers of an event"""
        try:
            # Notify type-specific subscribers
            if event.event_type in self.subscribers:
                for callback in self.subscribers[event.event_type]:
                    try:
                        await callback(event)
                    except Exception as e:
                        logger.error(f"Error in event callback: {e}")
            
            # Notify global subscribers
            for callback in self.global_subscribers:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"Error in global event callback: {e}")
            
            # Notify WebSocket connections
            await self._notify_websockets(event)
            
        except Exception as e:
            logger.error(f"Error notifying subscribers: {e}")
    
    async def _notify_websockets(self, event: Event):
        """Notify WebSocket connections"""
        if not self.websocket_connections:
            return
        
        message = event.to_json()
        disconnected = []
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)
    
    async def add_websocket_connection(self, websocket):
        """Add WebSocket connection for real-time updates"""
        self.websocket_connections.append(websocket)
        logger.info(f"WebSocket connection added. Total: {len(self.websocket_connections)}")
        
        # Send connection event
        await self.emit(EventType.WEBSOCKET_CONNECTED, "WebSocket client connected")
    
    async def remove_websocket_connection(self, websocket):
        """Remove WebSocket connection"""
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)
            logger.info(f"WebSocket connection removed. Total: {len(self.websocket_connections)}")
            
            # Send disconnection event
            await self.emit(EventType.WEBSOCKET_DISCONNECTED, "WebSocket client disconnected")
    
    async def _log_event(self, event: Event):
        """Log event to database and memory"""
        try:
            # Log to database
            await db_ops.log_event(
                event_type=event.event_type.value,
                message=event.message,
                data=event.data,
                severity=event.severity.value,
                source=event.source
            )
            
            # Log to memory
            self.event_log.append(event)
            
            # Trim log if too large
            if len(self.event_log) > self.max_log_size:
                self.event_log = self.event_log[-self.max_log_size:]
            
        except Exception as e:
            logger.error(f"Error logging event: {e}")
    
    async def get_event_log(self, limit: int = 100, event_type: Optional[EventType] = None,
                          severity: Optional[EventSeverity] = None) -> List[Event]:
        """Get event log with optional filtering"""
        try:
            events = self.event_log
            
            # Filter by event type
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            # Filter by severity
            if severity:
                events = [e for e in events if e.severity == severity]
            
            # Return most recent events first
            return events[-limit:] if limit else events
            
        except Exception as e:
            logger.error(f"Error getting event log: {e}")
            return []
    
    async def clear_event_log(self):
        """Clear event log"""
        try:
            self.event_log.clear()
            logger.info("Event log cleared")
            
        except Exception as e:
            logger.error(f"Error clearing event log: {e}")
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            # Count events by type
            event_counts = {}
            for event in self.event_log:
                event_type = event.event_type.value
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            # Count events by severity
            severity_counts = {}
            for event in self.event_log:
                severity = event.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            return {
                "total_events": len(self.event_log),
                "event_types": event_counts,
                "severity_counts": severity_counts,
                "websocket_connections": len(self.websocket_connections),
                "subscribers_count": sum(len(subs) for subs in self.subscribers.values()) + len(self.global_subscribers)
            }
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}


# Global event system instance
_event_system = None


def get_event_system() -> EventSystem:
    """Get the global event system instance"""
    global _event_system
    if _event_system is None:
        _event_system = EventSystem()
    return _event_system


# Convenience functions for common events
async def emit_system_status(message: str, data: Optional[Dict[str, Any]] = None):
    """Emit system status event"""
    event_system = get_event_system()
    await event_system.emit(EventType.SYSTEM_STATUS, message, data)


async def emit_chat_response(message: str, data: Optional[Dict[str, Any]] = None):
    """Emit chat response event"""
    event_system = get_event_system()
    await event_system.emit(EventType.CHAT_RESPONSE, message, data)


async def emit_training_started(message: str, data: Optional[Dict[str, Any]] = None):
    """Emit training started event"""
    event_system = get_event_system()
    await event_system.emit(EventType.TRAINING_STARTED, message, data)


async def emit_training_progress(message: str, data: Optional[Dict[str, Any]] = None):
    """Emit training progress event"""
    event_system = get_event_system()
    await event_system.emit(EventType.TRAINING_PROGRESS, message, data)


async def emit_training_completed(message: str, data: Optional[Dict[str, Any]] = None):
    """Emit training completed event"""
    event_system = get_event_system()
    await event_system.emit(EventType.TRAINING_COMPLETED, message, data)


async def emit_error(message: str, data: Optional[Dict[str, Any]] = None):
    """Emit error event"""
    event_system = get_event_system()
    await event_system.emit(EventType.ERROR_OCCURRED, message, data, EventSeverity.ERROR)


async def emit_audio_uploaded(message: str, data: Optional[Dict[str, Any]] = None):
    """Emit audio uploaded event"""
    event_system = get_event_system()
    await event_system.emit(EventType.AUDIO_UPLOADED, message, data)


async def emit_audio_processed(message: str, data: Optional[Dict[str, Any]] = None):
    """Emit audio processed event"""
    event_system = get_event_system()
    await event_system.emit(EventType.AUDIO_PROCESSED, message, data)
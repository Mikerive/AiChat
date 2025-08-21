"""
Core infrastructure package

Contains the foundational components: configuration, database, event system,
and logging setup.
"""

from .config import get_settings
from .database import get_db, DatabaseManager
from .event_system import get_event_system, EventType, EventSeverity

__all__ = [
    "get_settings",
    "get_db",
    "DatabaseManager",
    "get_event_system",
    "EventType",
    "EventSeverity",
]

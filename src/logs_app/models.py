"""
Pydantic models for logs app
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel


class LogEntry(BaseModel):
    """Model for log entry data

    Supports:
    - legacy message + severity
    - standardized http_code (e.g., 404, 500) which maps to severity levels
    - source to attribute logs (e.g., "frontend" or "backend")
    - optional error_code + params (kept for compatibility)
    """
    message: Optional[str] = None
    severity: str = "INFO"
    module: str = "api"
    timestamp: Optional[str] = None

    # Standardized fields
    http_code: Optional[int] = None  # Standard HTTP status code for the event (e.g., 404, 500)
    source: Optional[str] = None     # E.g., "frontend", "backend", "worker"

    # Backwards-compat: optional error_code + params from earlier design
    error_code: Optional[str] = None
    params: Optional[Dict[str, object]] = None


class LogResponse(BaseModel):
    """Model for log response data"""
    logs: List[Dict[str, str]]
    count: int
    log_file: str


class LogStats(BaseModel):
    """Model for log statistics"""
    total_entries: int
    severity_counts: Dict[str, int]
    module_counts: Dict[str, int]
    file_size: int
    oldest_entry: Optional[str]
    newest_entry: Optional[str]


class LogFilter(BaseModel):
    """Model for log filtering parameters"""
    limit: int = 100
    severity: Optional[str] = None
    module: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
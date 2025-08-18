"""
Pydantic models for logs app
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel


class LogEntry(BaseModel):
    """Model for log entry data"""
    message: str
    severity: str = "INFO"
    module: str = "api"
    timestamp: Optional[str] = None


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
"""
Logs App Module

Provides centralized logging functionality as a standalone application with REST API endpoints
"""

from .main import app as logs_app
from .models import LogEntry, LogResponse
from .service import LogsService

__all__ = ["logs_app", "LogEntry", "LogResponse", "LogsService"]
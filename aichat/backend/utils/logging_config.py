"""
Improved logging configuration to reduce redundant messages and improve clarity
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Set
import sys


class DuplicateFilter(logging.Filter):
    """Filter to suppress duplicate log messages within a time window"""

    def __init__(self, time_window_seconds: int = 30):
        super().__init__()
        self.time_window = timedelta(seconds=time_window_seconds)
        self.message_cache: Dict[str, datetime] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out duplicate messages within the time window"""
        message_key = f"{record.levelname}:{record.name}:{record.getMessage()}"
        now = datetime.now()

        # Check if we've seen this message recently
        if message_key in self.message_cache:
            last_seen = self.message_cache[message_key]
            if now - last_seen < self.time_window:
                return False  # Suppress this duplicate message

        # Update cache
        self.message_cache[message_key] = now

        # Clean old entries (every 100 messages to avoid memory buildup)
        if len(self.message_cache) % 100 == 0:
            cutoff = now - self.time_window
            self.message_cache = {
                k: v for k, v in self.message_cache.items() if v > cutoff
            }

        return True


class ServiceInitializationFilter(logging.Filter):
    """Filter to show only the first initialization of each service type"""

    def __init__(self):
        super().__init__()
        self.initialized_services: Set[str] = set()

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out repeated service initialization messages"""
        message = record.getMessage()

        # Check for service initialization patterns
        if "model loaded" in message.lower() or "initialized" in message.lower():
            service_type = None

            if "Whisper model" in message:
                service_type = "whisper"
            elif "Piper TTS" in message:
                service_type = "piper_tts"
            elif "Service Manager" in message:
                service_type = "service_manager"
            elif "Database initialized" in message:
                service_type = "database"

            if service_type:
                if service_type in self.initialized_services:
                    return False  # Suppress repeated initialization
                else:
                    self.initialized_services.add(service_type)
                    return True

        return True  # Allow all other messages


def setup_logging(log_level: str = "INFO") -> None:
    """Setup improved logging configuration with duplicate filtering"""

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    # Add filters to reduce noise
    duplicate_filter = DuplicateFilter(
        time_window_seconds=10
    )  # Suppress duplicates within 10 seconds
    service_init_filter = ServiceInitializationFilter()

    console_handler.addFilter(duplicate_filter)
    console_handler.addFilter(service_init_filter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addHandler(console_handler)

    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("database").setLevel(logging.WARNING)  # Reduce database noise

    logging.info("Improved logging configuration applied")

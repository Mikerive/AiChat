"""
Configuration management for VTuber backend
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from constants.paths import PROJECT_ROOT, BACKEND_SRC, PIPER_MODELS

# pydantic v2 moved BaseSettings to the pydantic-settings package.
# Provide a compatibility import that works with v1 and v2 installs.
try:
    from pydantic import Field
    try:
        from pydantic import BaseSettings  # pydantic v1 or compatible v2 shim
    except Exception:
        from pydantic_settings import BaseSettings
except Exception:
    # Fallback — attempt direct import (older environments)
    from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    api_host: str = Field(default="localhost", env="API_HOST")
    api_port: int = Field(default=8765, env="API_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///vtuber.db", env="DATABASE_URL")
    
    # Audio Configuration
    sample_rate: int = Field(default=16000, env="SAMPLE_RATE")
    channels: int = Field(default=1, env="CHANNELS")
    vad_mode: int = Field(default=2, env="VAD_MODE")
    speech_timeout: float = Field(default=1.0, env="SPEECH_TIMEOUT")
    
    # Model Configuration
    whisper_model: str = Field(default="base", env="WHISPER_MODEL")
    piper_model_path: Path = Field(default=PIPER_MODELS / "en_US-amy-medium.onnx", env="PIPER_MODEL_PATH")
    
    # Paths Configuration
    models_dir: Path = Field(default=BACKEND_SRC / "chat" / "models", env="MODELS_DIR")
    log_file: Path = Field(default=PROJECT_ROOT / "logs" / "vtuber.log", env="LOG_FILE")
    data_dir: Path = Field(default=PROJECT_ROOT / "data", env="DATA_DIR")
    
    # Character Configuration
    character_name: str = Field(default="Miku", env="CHARACTER_NAME")
    character_profile: str = Field(default="hatsune_miku", env="CHARACTER_PROFILE")
    use_character_profiles: bool = Field(default=True, env="USE_CHARACTER_PROFILES")
    character_personality: str = Field(default="cheerful,curious,helpful", env="CHARACTER_PERSONALITY")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # OpenRouter Configuration (for LLM)
    openrouter_api_key: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="qwen/qwen-2.5-7b-instruct", env="OPENROUTER_MODEL")
    openrouter_url: str = Field(default="https://openrouter.ai/api/v1/chat/completions", env="OPENROUTER_URL")
    
    # CORS Configuration
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow unrelated environment variables to be present (e.g., HOST/PORT) without failing validation
        extra = "ignore"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Ensure directories exist
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        log_dir = self.log_file.parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info(f"Logging initialized - Level: {self.log_level}, File: {self.log_file}")
    
    def get_cors_middleware_config(self) -> Dict[str, Any]:
        """Get CORS middleware configuration"""
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }
    
    def get_openrouter_config(self) -> Dict[str, Any]:
        """Get OpenRouter configuration"""
        return {
            "api_key": self.openrouter_api_key,
            "model": self.openrouter_model,
            "url": self.openrouter_url,
        }
    
    def get_audio_config(self) -> Dict[str, Any]:
        """Get audio processing configuration"""
        return {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "vad_mode": self.vad_mode,
            "speech_timeout": self.speech_timeout,
        }
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration"""
        return {
            "whisper_model": self.whisper_model,
            "piper_model_path": str(self.piper_model_path),
            "models_dir": str(self.models_dir),
        }
    
    def get_character_config(self) -> Dict[str, Any]:
        """Get character configuration"""
        return {
            "character_name": self.character_name,
            "character_profile": self.character_profile,
            "use_character_profiles": self.use_character_profiles,
            "character_personality": self.character_personality,
        }


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get the global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def create_settings_from_env() -> Settings:
    """Create settings from environment variables"""
    return Settings()


# Configuration validation
def validate_config() -> bool:
    """Validate configuration settings"""
    try:
        settings = get_settings()
        
        # Check required settings
        if not settings.openrouter_api_key:
            logger.warning("OpenRouter API key not configured - LLM functionality will be limited")
        
        # Check model paths
        piper_path = Path(settings.piper_model_path)
        if not piper_path.exists():
            logger.warning(f"Piper model not found at: {settings.piper_model_path}")
        
        # Check database URL
        if not settings.database_url.startswith("sqlite:///"):
            logger.warning(f"Unsupported database URL: {settings.database_url}")
        
        logger.info("Configuration validation completed")
        return True
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False


# Initialize configuration on module import
try:
    settings = get_settings()
    logger = logging.getLogger(__name__)
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Error loading configuration: {e}")
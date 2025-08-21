from pathlib import Path

# Project-level paths and centralized constants for file locations

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
AICHAT_DIR = PROJECT_ROOT / "aichat"

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = DATA_DIR / "logs"

# Audio directories
AUDIO_DIR = DATA_DIR / "audio"
MODELS_DIR = AUDIO_DIR / "models"
GENERATED_AUDIO_DIR = AUDIO_DIR / "generated"

# Training directories
TRAINING_DATA_DIR = DATA_DIR / "training"
TTS_TRAINING_RAW = TRAINING_DATA_DIR / "raw"
TTS_TRAINING_PROCESSED = TRAINING_DATA_DIR / "processed"
TTS_TRAINING_METADATA = TRAINING_DATA_DIR / "metadata.csv"
TTS_TRAINING_CHECKPOINTS = TRAINING_DATA_DIR / "checkpoints"

# Temporary directories
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_AUDIO_DIR = TEMP_DIR / "audio"

# Test data
TEST_DATA_DIR = PROJECT_ROOT / "tests" / "fixtures"


# Ensure directories exist (callers may call .mkdir as needed)
def ensure_dirs(*paths):
    """Create directories for given Path objects if they don't exist."""
    for p in paths:
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Best-effort; ignore errors here and let callers handle failures
            pass


__all__ = [
    # Core directories
    "PROJECT_ROOT",
    "AICHAT_DIR",
    "DATA_DIR",
    "CONFIG_DIR",
    "LOGS_DIR",
    # Audio directories
    "AUDIO_DIR",
    "MODELS_DIR",
    "GENERATED_AUDIO_DIR",
    # Training directories
    "TRAINING_DATA_DIR",
    "TTS_TRAINING_RAW",
    "TTS_TRAINING_PROCESSED",
    "TTS_TRAINING_METADATA",
    "TTS_TRAINING_CHECKPOINTS",
    # Temporary directories
    "TEMP_DIR",
    "TEMP_AUDIO_DIR",
    # Test directories
    "TEST_DATA_DIR",
    # Utilities
    "ensure_dirs",
]

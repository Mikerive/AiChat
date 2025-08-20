from pathlib import Path

# Project-level paths and centralized constants for file locations

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
SRC_DIR = PROJECT_ROOT / "src"
BACKEND_SRC = SRC_DIR / "backend"

# Temporary directories
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_AUDIO_DIR = TEMP_DIR / "audio"

# TTS finetune app paths
TTS_TRAINING_DIR = BACKEND_SRC / "tts_finetune_app" / "training_data"
TTS_TRAINING_RAW = TTS_TRAINING_DIR / "raw"
TTS_TRAINING_PROCESSED = TTS_TRAINING_DIR / "processed"
TTS_TRAINING_METADATA = TTS_TRAINING_DIR / "metadata.csv"
TTS_TRAINING_CHECKPOINTS = TTS_TRAINING_DIR / "checkpoints"
TTS_MODELS_DIR = BACKEND_SRC / "tts_finetune_app" / "models"
TTS_PIPER_DATASET = BACKEND_SRC / "tts_finetune_app" / "piper_dataset"
TTS_LOGS_DIR = BACKEND_SRC / "tts_finetune_app" / "logs"

# Piper TTS related paths
PIPER_MODELS = BACKEND_SRC / "chat_app" / "audio" / "piper_models"
AUDIO_OUTPUT = BACKEND_SRC / "chat_app" / "audio" / "generated"

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
    "PROJECT_ROOT",
    "SRC_DIR",
    "BACKEND_SRC",
    "TEMP_DIR",
    "TEMP_AUDIO_DIR",
    "TTS_TRAINING_DIR",
    "TTS_TRAINING_RAW",
    "TTS_TRAINING_PROCESSED",
    "TTS_TRAINING_METADATA",
    "TTS_TRAINING_CHECKPOINTS",
    "TTS_MODELS_DIR",
    "TTS_PIPER_DATASET",
    "TTS_LOGS_DIR",
    "PIPER_MODELS",
    "AUDIO_OUTPUT",
    "ensure_dirs",
]
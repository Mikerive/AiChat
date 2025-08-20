try:
    from src.constants.paths import *  # type: ignore
except Exception:
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.resolve()
    SRC_DIR = PROJECT_ROOT / "src"
    BACKEND_SRC = SRC_DIR / "backend"

    TEMP_DIR = PROJECT_ROOT / "temp"
    TEMP_AUDIO_DIR = TEMP_DIR / "audio"

    TTS_TRAINING_DIR = BACKEND_SRC / "tts_finetune_app" / "training_data"
    TTS_TRAINING_RAW = TTS_TRAINING_DIR / "raw"
    TTS_TRAINING_PROCESSED = TTS_TRAINING_DIR / "processed"
    TTS_TRAINING_METADATA = TTS_TRAINING_DIR / "metadata.csv"
    TTS_TRAINING_CHECKPOINTS = TTS_TRAINING_DIR / "checkpoints"

    TTS_MODELS_DIR = BACKEND_SRC / "tts_finetune_app" / "models"
    TTS_PIPER_DATASET = BACKEND_SRC / "tts_finetune_app" / "piper_dataset"
    TTS_LOGS_DIR = BACKEND_SRC / "tts_finetune_app" / "logs"

    PIPER_MODELS = BACKEND_SRC / "chat_app" / "audio" / "piper_models"
    AUDIO_OUTPUT = BACKEND_SRC / "chat_app" / "audio" / "generated"

    def ensure_dirs(*paths):
        for p in paths:
            try:
                p.mkdir(parents=True, exist_ok=True)
            except Exception:
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
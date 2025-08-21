"""
Compatibility re-export

The implementation lives in:
  backend.tts_finetune_app.processors.audio_processor

This module re-exports AudioProcessor and TrainingConfig so existing imports
using backend.tts_finetune_app.audio_processor continue to work while there
is a single authoritative implementation.
"""

import logging
from importlib import import_module

logger = logging.getLogger(__name__)

try:
    mod = import_module("backend.tts_finetune_app.processors.audio_processor")
    AudioProcessor = getattr(mod, "AudioProcessor")
    TrainingConfig = getattr(mod, "TrainingConfig")
    logger.info(
        "Re-exported AudioProcessor from backend.tts_finetune_app.processors.audio_processor"
    )
except Exception as e:
    logger.error(f"Failed to import audio_processor implementation: {e}")
    raise

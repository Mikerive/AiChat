"""
TTS Finetune App package

Provides structured submodules:
- processors: audio/video processing and segmentation
- services: high-level orchestration/service wrappers
- controllers: optional HTTP controllers (kept separate from main API routes)
- models: dataclasses / schemas used by the package
- scripts: CLI scripts for ingestion, preprocessing, transcription, manifest generation, and training

This package is intentionally thin: heavy lifting remains in processors/ and scripts/.
"""

__all__ = ["processors", "services", "controllers", "models", "scripts"]

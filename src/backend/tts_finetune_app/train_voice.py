"""Compatibility wrapper for VoiceTrainer.

This module will try to import the legacy implementation from backend.voice_trainer.train_voice.
If that import fails (the legacy module is intentionally removed in some refactors),
provide lightweight fallback implementations sufficient for tests and simple usage.
"""

from typing import Optional, Dict, Any

try:
    from backend.voice_trainer.train_voice import VoiceTrainer as _VoiceTrainer, VoiceTrainerConfig as _VoiceTrainerConfig  # type: ignore
except Exception:
    _VoiceTrainer = None  # type: ignore
    _VoiceTrainerConfig = None  # type: ignore

if _VoiceTrainer is not None and _VoiceTrainerConfig is not None:
    class VoiceTrainer(_VoiceTrainer):
        """Wrapper for backward-compatible import path."""
        pass

    class VoiceTrainerConfig(_VoiceTrainerConfig):
        pass

else:
    # Fallback minimal implementations used in tests / lightweight usage.
    class VoiceTrainerConfig:
        """Minimal configuration placeholder for VoiceTrainer."""
        def __init__(self,
                     dataset_dir: Optional[str] = None,
                     output_dir: Optional[str] = None,
                     model_name: Optional[str] = None,
                     sample_rate: int = 22050,
                     **kwargs):
            self.dataset_dir = dataset_dir
            self.output_dir = output_dir
            self.model_name = model_name
            self.sample_rate = sample_rate
            for k, v in kwargs.items():
                setattr(self, k, v)

    class VoiceTrainer:
        """Minimal VoiceTrainer shim that provides the same import surface
        but does not perform heavy training. Useful for tests that only need
        the class to exist.
        """
        def __init__(self, config: Optional[VoiceTrainerConfig] = None):
            self.config = config or VoiceTrainerConfig()
            self.state: Dict[str, Any] = {"initialized": True}

        def prepare_dataset(self):
            """No-op dataset preparation."""
            return {"status": "skipped", "reason": "no-op in test shim"}

        def train(self, epochs: int = 1):
            """No-op train method that returns a stubbed result."""
            return {"status": "skipped", "epochs": epochs}

        def export_model(self, path: str):
            """No-op export"""
            return {"status": "skipped", "path": path}

__all__ = ["VoiceTrainer", "VoiceTrainerConfig"]
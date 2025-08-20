"""
Service layer for TTS finetune operations.

Refactored to delegate to the in-repo orchestrator service:
  backend.tts_finetune_app.services.runner.TTSOrchestratorService

This keeps cross-package subprocess logic inside the tts_finetune_app package
and uses a thin adapter in the chat_app.services layer.
"""
from pathlib import Path
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

try:
    from backend.tts_finetune_app.services.runner import TTSOrchestratorService
    _ORCHESTRATOR_AVAILABLE = True
except Exception as e:
    logger.warning(f"TTS orchestrator service not available: {e}")
    TTSOrchestratorService = None
    _ORCHESTRATOR_AVAILABLE = False


class TTSFinetuneService:
    """
    Adapter that exposes generate_manifest and start_training by delegating
    to backend.tts_finetune_app.services.runner.TTSOrchestratorService.
    """

    def __init__(self, python_exec: str = "python"):
        if not _ORCHESTRATOR_AVAILABLE:
            raise RuntimeError("TTS orchestrator service not available")
        self._orch = TTSOrchestratorService(python_executable=python_exec)

    def generate_manifest(self,
                          input_dir: Path,
                          metadata_csv: Optional[Path],
                          output_dir: Path,
                          sample_rate: int = 22050,
                          fmt: str = "both",
                          resample: bool = False,
                          copy_audio: bool = False) -> Dict:
        return self._orch.generate_manifest(
            input_dir=input_dir,
            metadata_csv=metadata_csv,
            output_dir=output_dir,
            sample_rate=sample_rate,
            fmt=fmt,
            resample=resample,
            copy_audio=copy_audio
        )

    def start_training(self,
                       dataset_dir: Path,
                       output_dir: Path,
                       model_name: str,
                       preprocess: bool = False,
                       language: str = "en-us",
                       dataset_format: str = "ljspeech",
                       sample_rate: int = 22050,
                       accelerator: str = "gpu",
                       devices: int = 1,
                       batch_size: int = 12,
                       checkpoint_epochs: int = 1,
                       log_every_n_steps: int = 1000,
                       max_epochs: int = 10000,
                       resume_from_checkpoint: str = "",
                       quality: str = "medium",
                       extra_args: Optional[List[str]] = None) -> Dict:
        return self._orch.start_training(
            dataset_dir=dataset_dir,
            output_dir=output_dir,
            model_name=model_name,
            preprocess=preprocess,
            language=language,
            dataset_format=dataset_format,
            sample_rate=sample_rate,
            accelerator=accelerator,
            devices=devices,
            batch_size=batch_size,
            checkpoint_epochs=checkpoint_epochs,
            log_every_n_steps=log_every_n_steps,
            max_epochs=max_epochs,
            resume_from_checkpoint=resume_from_checkpoint,
            quality=quality,
            extra_args=extra_args
        )
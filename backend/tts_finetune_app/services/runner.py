"""
TTS Orchestrator Service (inside backend.tts_finetune_app.services)

Provides high-level programmatic operations for:
- manifest generation
- training orchestration

This centralizes script invocation inside the package so external controllers/services
can call into the package without directly running subprocesses against script files.
"""
from pathlib import Path
import subprocess
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TTSOrchestratorService:
    def __init__(self, python_executable: str = "python"):
        self.python = python_executable
        # scripts directory relative to this file
        # parent[1] refers to the tts_finetune_app package directory (where scripts live)
        self.scripts_dir = Path(__file__).resolve().parents[1] / "scripts"

    def _run_script(self, script_name: str, args: List[str]) -> Dict:
        script = self.scripts_dir / script_name
        cmd = [self.python, str(script)] + args
        logger.info("Running script: %s", " ".join(cmd))
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            logger.error("Script %s failed: %s", script_name, proc.stderr[:1000])
            raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr)
        return {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}

    def generate_manifest(self,
                          input_dir: Path,
                          metadata_csv: Optional[Path],
                          output_dir: Path,
                          sample_rate: int = 22050,
                          fmt: str = "both",
                          resample: bool = False,
                          copy_audio: bool = False) -> Dict:
        args = [
            "--input-dir", str(input_dir),
            "--output-dir", str(output_dir),
            "--sample-rate", str(sample_rate),
            "--format", fmt
        ]
        if metadata_csv:
            args.extend(["--metadata-csv", str(metadata_csv)])
        if resample:
            args.append("--resample")
        if copy_audio:
            args.append("--copy-audio")

        return self._run_script("generate_piper_manifest.py", args)

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
        extra_args = extra_args or []
        args = [
            "--dataset-dir", str(dataset_dir),
            "--output-dir", str(output_dir),
            "--model-name", model_name,
            "--language", language,
            "--dataset-format", dataset_format,
            "--sample-rate", str(sample_rate),
            "--accelerator", accelerator,
            "--devices", str(devices),
            "--batch-size", str(batch_size),
            "--checkpoint-epochs", str(checkpoint_epochs),
            "--log-every-n-steps", str(log_every_n_steps),
            "--max-epochs", str(max_epochs),
            "--quality", quality
        ]
        if preprocess:
            args.append("--preprocess")
        if resume_from_checkpoint:
            args.extend(["--resume-from-checkpoint", str(resume_from_checkpoint)])
        if extra_args:
            args.extend(extra_args)

        return self._run_script("train_orchestrator.py", args)
#!/usr/bin/env python3
"""
Training orchestrator for Piper fine-tuning.

Responsibilities:
- Prepare dataset for Piper using `piper_train.preprocess`
- Launch Piper training (`piper_train`) with checkpointing and resume support
- Stream logs to a file and update a job checkpoint JSON so long runs can be resumed/monitored
- Provide sensible defaults and a CLI interface

Notes:
- This script expects `piper_train` to be importable as a module on PATH (i.e., Piper repo installed) or
  the `piper_train` console script to be available. It uses subprocess to invoke the commands.
- Checkpoints and logs are stored under the training output directory.
- For robust long-run deployments, run this under a process manager or background task.
"""
from pathlib import Path
import argparse
import subprocess
import json
import tempfile
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("train_orchestrator")

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_PIPER_DATASET = BASE_DIR / "piper_dataset"
DEFAULT_OUTPUT_DIR = BASE_DIR / "models"

def atomic_write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tmp:
        tmp.write(json.dumps(obj, indent=2))
        tmp.flush()
        tmp_name = Path(tmp.name)
    tmp_name.replace(path)

def update_job_json(job_path: Path, updates: dict):
    job = {}
    if job_path.exists():
        try:
            job = json.loads(job_path.read_text(encoding="utf-8"))
        except Exception:
            job = {}
    job.setdefault("updated_at", datetime.utcnow().isoformat() + "Z")
    job.setdefault("history", []).append({"ts": datetime.utcnow().isoformat() + "Z", "update": updates})
    atomic_write_json(job_path, job)

def run_preprocess(input_dir: Path, output_dir: Path, language: str, dataset_format: str, sample_rate: int, single_speaker: bool, extra_args: list):
    """
    Run Piper's preprocess step:
    python -m piper_train.preprocess --language en-us --input-dir <input> --output-dir <output> --dataset-format ljspeech --sample-rate 22050 [--single-speaker]
    """
    cmd = [
        "python", "-m", "piper_train.preprocess",
        "--language", language,
        "--input-dir", str(input_dir),
        "--output-dir", str(output_dir),
        "--dataset-format", dataset_format,
        "--sample-rate", str(sample_rate)
    ]
    if single_speaker:
        cmd.append("--single-speaker")
    if extra_args:
        cmd.extend(extra_args)

    logger.info("Running Piper preprocess: %s", " ".join(cmd))
    proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    logger.info("Preprocess complete")
    return proc.stdout

def run_training(dataset_dir: Path, output_dir: Path, accelerator: str, devices: int, batch_size: int, validation_split: float,
                 checkpoint_epochs: int, log_every_n_steps: int, max_epochs: int, resume_from_checkpoint: str, quality: str, extra_args: list, log_path: Path, job_path: Path):
    """
    Run the Piper training command via subprocess and stream logs to a file.
    Returns the process exit code.
    """
    cmd = [
        "python", "-m", "piper_train",
        "--dataset-dir", str(dataset_dir),
        "--accelerator", accelerator,
        "--devices", str(devices),
        "--batch-size", str(batch_size),
        "--validation-split", str(validation_split),
        "--checkpoint-epochs", str(checkpoint_epochs),
        "--log-every-n-steps", str(log_every_n_steps),
        "--max_epochs", str(max_epochs),
        "--quality", quality
    ]

    if resume_from_checkpoint:
        cmd.extend(["--resume_from_checkpoint", resume_from_checkpoint])
    if extra_args:
        cmd.extend(extra_args)

    logger.info("Launching Piper training: %s", " ".join(cmd))

    # Ensure log dir exists
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as logf:
        logf.write(f"\n\n--- Training started at {datetime.utcnow().isoformat()}Z ---\n")
        logf.flush()
        # Launch process streaming stdout/stderr
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

        # Stream to file and stdout
        try:
            for line in proc.stdout:
                logf.write(line)
                logf.flush()
                logger.info(line.rstrip())
                # Simple heuristic: if a checkpoint file was just created, note it (implementation-specific)
                # Update job JSON periodically to show training is alive
                update_job_json(job_path, {"training_log_tail": line[:200]})
        except Exception as e:
            logger.error(f"Error streaming training logs: {e}")
            proc.kill()
            raise

        ret = proc.wait()
        logf.write(f"\n--- Training finished at {datetime.utcnow().isoformat()}Z (exit {ret}) ---\n")
        logf.flush()

    logger.info("Training process exited with code %s", ret)
    return ret

def main():
    parser = argparse.ArgumentParser(description="Train orchestrator for Piper fine-tuning")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_PIPER_DATASET, help="Preprocessed Piper dataset dir (output of preprocess step)")
    parser.add_argument("--raw-input-dir", type=Path, default=BASE_DIR / "training_data", help="Raw training data directory (used if preprocessing is requested)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Where to store trained models and checkpoints")
    parser.add_argument("--model-name", type=str, default=f"piper_finetune_{int(time.time())}", help="Name for the output model folder")
    parser.add_argument("--language", type=str, default="en-us", help="Language for preprocessing")
    parser.add_argument("--dataset-format", choices=["ljspeech","mycroft"], default="ljspeech", help="Dataset format for Piper preprocess")
    parser.add_argument("--sample-rate", type=int, default=22050, choices=[16000,22050], help="Sample rate for dataset")
    parser.add_argument("--preprocess", action="store_true", help="Run preprocessing step before training")
    parser.add_argument("--single-speaker", action="store_true", help="Mark dataset as single-speaker for Piper preprocess")
    parser.add_argument("--accelerator", type=str, default="gpu", choices=["gpu","cpu"], help="Accelerator for training")
    parser.add_argument("--devices", type=int, default=1, help="Number of devices (GPUs) to use")
    parser.add_argument("--batch-size", type=int, default=12, help="Batch size")
    parser.add_argument("--validation-split", type=float, default=0.01)
    parser.add_argument("--checkpoint-epochs", type=int, default=1)
    parser.add_argument("--log-every-n-steps", type=int, default=1000)
    parser.add_argument("--max-epochs", type=int, default=10000)
    parser.add_argument("--resume-from-checkpoint", type=str, default="", help="Path to checkpoint to resume from")
    parser.add_argument("--quality", type=str, default="medium", choices=["high","medium","x-low"], help="Model quality")
    parser.add_argument("--extra-args", nargs="*", default=[], help="Extra arguments passed to underlying commands")
    parser.add_argument("--log-file", type=Path, default=None, help="Training log file path")
    args = parser.parse_args()

    # Prepare paths
    model_output = Path(args.output_dir) / args.model_name
    model_output.mkdir(parents=True, exist_ok=True)

    # Job checkpoint JSON
    job_path = model_output / "job_checkpoint.json"
    update_job_json(job_path, {"action": "start", "model_name": args.model_name, "ts": datetime.utcnow().isoformat() + "Z"})

    # run preprocess if requested
    if args.preprocess:
        preprocess_output = args.dataset_dir
        logger.info("Running preprocess step")
        try:
            preprocess_stdout = run_preprocess(args.raw_input_dir, preprocess_output, args.language, args.dataset_format, args.sample_rate, args.single_speaker, args.extra_args)
            # Save preprocess stdout to job
            (model_output / "preprocess_stdout.txt").write_text(preprocess_stdout, encoding="utf-8")
            update_job_json(job_path, {"preprocess": "completed"})
        except subprocess.CalledProcessError as e:
            logger.error(f"Preprocess failed: {e}")
            update_job_json(job_path, {"preprocess": "failed", "error": str(e)})
            return

    # Determine log file
    if args.log_file:
        log_path = args.log_file
    else:
        log_path = model_output / "training.log"

    # Run training
    try:
        ret = run_training(
            dataset_dir=args.dataset_dir,
            output_dir=model_output,
            accelerator=args.accelerator,
            devices=args.devices,
            batch_size=args.batch_size,
            validation_split=args.validation_split,
            checkpoint_epochs=args.checkpoint_epochs,
            log_every_n_steps=args.log_every_n_steps,
            max_epochs=args.max_epochs,
            resume_from_checkpoint=args.resume_from_checkpoint,
            quality=args.quality,
            extra_args=args.extra_args,
            log_path=log_path,
            job_path=job_path
        )
        update_job_json(job_path, {"training_exit_code": ret})
    except Exception as e:
        logger.error(f"Training orchestration failed: {e}")
        update_job_json(job_path, {"training_failed": str(e)})
        return

    logger.info("Training orchestration finished. Output saved to %s", model_output)

if __name__ == "__main__":
    main()
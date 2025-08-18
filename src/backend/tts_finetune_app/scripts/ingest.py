#!/usr/bin/env python3
"""
Ingest script for TTS finetune pipeline.

- Accepts an input audio/video file (mp3/mp4/...), extracts a WAV at the target sample rate
  into backend/tts_finetune_app/training_data/raw/
- Computes checksum (sha256) of the original file
- Creates a job checkpoint JSON in backend/tts_finetune_app/checkpoints/<job_id>.json
- Uses atomic writes for checkpoint files
"""
from pathlib import Path
import argparse
import subprocess
import hashlib
import json
import uuid
import shutil
import tempfile
import sys
from datetime import datetime

# Configuration defaults
DEFAULT_SAMPLE_RATE = 22050
BASE_DIR = Path(__file__).resolve().parents[2]  # backend/tts_finetune_app/scripts -> ../..
TRAINING_DATA_DIR = BASE_DIR / "training_data"
RAW_DIR = TRAINING_DATA_DIR / "raw"
CHECKPOINTS_DIR = BASE_DIR / "checkpoints"


def ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_audio_to_wav(input_path: Path, output_wav: Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> Path:
    """
    Use ffmpeg to extract/convert audio to mono WAV at sample_rate.
    Returns the output_wav path on success or raises CalledProcessError.
    """
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vn", "-ac", "1", "-ar", str(sample_rate),
        str(output_wav)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_wav


def atomic_write_json(path: Path, data: dict):
    """
    Atomic write: write to temp file then move to final path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tmp:
        tmp.write(json.dumps(data, indent=2))
        tmp.flush()
    tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def create_job_checkpoint(job_id: str, original_filename: str, checksum: str, duration_seconds: float = None) -> Path:
    job = {
        "job_id": job_id,
        "original_filename": original_filename,
        "checksum": checksum,
        "ingested_at": datetime.utcnow().isoformat() + "Z",
        "duration_seconds": duration_seconds,
        "stages": {
            "ingested": True,
            "separated": False,
            "segments_saved": 0,
            "transcribed_count": 0,
            "manifest_created": False,
            "training": {"epoch": 0, "last_checkpoint": None}
        }
    }
    job_path = CHECKPOINTS_DIR / f"{job_id}.json"
    atomic_write_json(job_path, job)
    return job_path


def probe_duration_seconds(path: Path) -> float:
    """
    Use ffprobe to get duration. Returns float seconds or None if not available.
    """
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path)
        ]
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = result.stdout.decode().strip()
        return float(out) if out else None
    except Exception:
        return None


def ingest_file(input_file: Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> dict:
    ensure_dirs()
    if not input_file.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    job_id = uuid.uuid4().hex[:12]
    checksum = compute_sha256(input_file)

    # Determine output wav path
    out_name = f"{input_file.stem}_{job_id}.wav"
    output_wav = RAW_DIR / out_name

    # Extract/convert
    try:
        extract_audio_to_wav(input_file, output_wav, sample_rate=sample_rate)
    except subprocess.CalledProcessError as e:
        # If ffmpeg failed, try a fallback: copy if already wav
        if input_file.suffix.lower() == ".wav":
            shutil.copy2(str(input_file), str(output_wav))
        else:
            raise

    # Probe duration
    duration = probe_duration_seconds(output_wav)

    # Create job checkpoint
    job_path = create_job_checkpoint(job_id, str(input_file.name), checksum, duration)

    return {
        "job_id": job_id,
        "original": str(input_file),
        "wav": str(output_wav),
        "checksum": checksum,
        "duration_seconds": duration,
        "job_path": str(job_path)
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest audio/video file for TTS finetune pipeline")
    parser.add_argument("input", type=Path, help="Path to input file (mp3/mp4/wav/...)")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE, help="Output sample rate (Hz)")
    args = parser.parse_args()

    try:
        result = ingest_file(args.input, sample_rate=args.sample_rate)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
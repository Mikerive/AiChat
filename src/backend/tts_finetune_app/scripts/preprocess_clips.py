#!/usr/bin/env python3
"""
Preprocess saved audio clips for TTS training.

- Scans backend/tts_finetune_app/training_data/audio/ for clips (wav)
- For each clip:
  - Loads at target sample rate
  - Normalizes RMS
  - Optional spectral gating denoise (uses noisereduce if available)
  - Trims leading/trailing silence
  - Saves atomically to training_data/processed/
  - Updates a per-clip JSON metadata file with duration and processing timestamp
  - Updates checkpoint JSON for job_id when provided via filename pattern (optional)
"""
from pathlib import Path
import argparse
import logging
import tempfile
import json
import shutil
import numpy as np
import soundfile as sf
import librosa

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parents[2]
TRAINING_DIR = BASE_DIR / "training_data"
AUDIO_DIR = TRAINING_DIR / "audio"
PROCESSED_DIR = TRAINING_DIR / "processed"
CHECKPOINTS_DIR = TRAINING_DIR / "checkpoints"

SAMPLE_RATE = 22050
MIN_AUDIO_LENGTH = 3.0  # seconds


def atomic_save_wav(path: Path, samples: np.ndarray, sr: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=str(path.parent)) as tmp:
        tmp_name = Path(tmp.name)
    sf.write(str(tmp_name), samples, sr, subtype="PCM_16")
    tmp_name.replace(path)


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    return librosa.util.normalize(audio)


def trim_silence(audio: np.ndarray, sr: int, top_db: int = 20) -> np.ndarray:
    trimmed, _ = librosa.effects.trim(audio, top_db=top_db)
    return trimmed


def denoise_audio(audio: np.ndarray, sr: int) -> np.ndarray:
    try:
        import noisereduce as nr
        reduced = nr.reduce_noise(y=audio, sr=sr)
        return reduced
    except Exception:
        logger.info("noisereduce not available; skipping denoise")
        return audio


def process_clip(in_path: Path, out_dir: Path, overwrite: bool = False) -> dict:
    try:
        audio, sr = librosa.load(str(in_path), sr=SAMPLE_RATE, mono=True)
        # Trim silence
        audio = trim_silence(audio, sr)
        # Normalize
        audio = normalize_audio(audio)
        # Denoise (optional)
        audio = denoise_audio(audio, sr)
        duration = len(audio) / sr
        if duration < MIN_AUDIO_LENGTH:
            logger.warning(f"Clip too short after processing ({duration:.2f}s): {in_path.name}")
            return {"status": "skipped", "reason": "too_short", "duration": duration}

        out_path = out_dir / in_path.name
        if out_path.exists() and not overwrite:
            logger.info(f"Processed file exists, skipping: {out_path}")
            return {"status": "exists", "path": str(out_path), "duration": duration}

        atomic_save_wav(out_path, audio, sr)

        # Write per-clip metadata JSON
        meta = {
            "filename": in_path.name,
            "processed_path": str(out_path),
            "duration_seconds": duration,
            "processed_at": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
        meta_path = out_dir / f"{in_path.stem}.json"
        with tempfile.NamedTemporaryFile("w", delete=False, dir=str(out_dir), encoding="utf-8") as tmp:
            tmp.write(json.dumps(meta, indent=2))
            tmp.flush()
            tmp_name = Path(tmp.name)
        tmp_name.replace(meta_path)

        logger.info(f"Processed and saved: {out_path}")
        return {"status": "ok", "path": str(out_path), "duration": duration}
    except Exception as e:
        logger.error(f"Failed processing {in_path}: {e}")
        return {"status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Process current queue and exit")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing processed files")
    parser.add_argument("--poll-interval", type=float, default=3.0)
    args = parser.parse_args()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    def run_once():
        for wav in sorted(AUDIO_DIR.glob("*.wav")):
            result = process_clip(wav, PROCESSED_DIR, overwrite=args.overwrite)
            # Optionally move original to processed/orig/
            if result.get("status") == "ok":
                orig_archive = AUDIO_DIR.parent / "archived"
                orig_archive.mkdir(parents=True, exist_ok=True)
                try:
                    wav.replace(orig_archive / wav.name)
                except Exception:
                    pass

    if args.once:
        run_once()
        return

    while True:
        run_once()
        import time
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    main()
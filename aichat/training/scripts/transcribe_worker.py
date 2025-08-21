#!/usr/bin/env python3
"""
Transcription worker: processes WAV files in a directory, transcribes using the project's Whisper service,
and appends rows to training_data/metadata.csv atomically as clips complete.

This script reuses the existing Whisper service if available at backend.chat_app.services.whisper_service.
If not available, it will raise and must be run within the application context that provides the service.
"""
import argparse
import csv
import logging
import tempfile
import time
from typing import Optional
from pathlib import Path

# Try to import the project's Whisper service
try:
    from aichat.backend.services.voice.stt.whisper_service import (
        VoiceService as WhisperService,
    )

    HAS_WHISPER = True
except Exception:
    HAS_WHISPER = False

TRAINING_DIR = Path(__file__).resolve().parents[2] / "training_data"
AUDIO_DIR = TRAINING_DIR / "audio"
METADATA_CSV = TRAINING_DIR / "metadata.csv"
POLL_INTERVAL = 3.0  # seconds

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def atomic_append_csv(csv_path: Path, row: list):
    """
    Append a row to CSV atomically by writing to a tmp file and then appending its contents.
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    # Write the single-row CSV to a temp file in same directory
    with tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(csv_path.parent), newline="", encoding="utf-8"
    ) as tmp:
        writer = csv.writer(tmp)
        writer.writerow(row)
        tmp_name = Path(tmp.name)
    # Append tmp file content to final CSV
    with csv_path.open("a", newline="", encoding="utf-8") as f_out, tmp_name.open(
        "r", encoding="utf-8"
    ) as f_in:
        f_out.write(f_in.read())
    try:
        tmp_name.unlink()
    except Exception:
        pass


class Transcriber:
    def __init__(self, whisper_model: Optional[str] = None):
        self.whisper_model = whisper_model
        if HAS_WHISPER:
            try:
                # Instantiate service (constructor signature may vary)
                self.whisper = WhisperService()
            except Exception:
                self.whisper = None
        else:
            self.whisper = None

    def transcribe_file(self, path: Path) -> dict:
        """
        Transcribe using local whisper service if available; otherwise raise.
        Returns dict with keys: text, language, confidence, duration
        """
        if self.whisper:
            try:
                res = self.whisper.transcribe_audio(path)
                # Some services return coroutine or dict; handle both
                if hasattr(res, "__await__"):
                    # async - run via asyncio
                    import asyncio

                    res = asyncio.get_event_loop().run_until_complete(res)
                return res
            except Exception as e:
                logger.warning(f"Whisper service transcribe failed for {path}: {e}")
                raise
        else:
            raise RuntimeError(
                "Whisper service not available in this environment. Please implement fallback or run inside app context."
            )


def read_seen_filenames(csv_path: Path):
    seen = set()
    if csv_path.exists():
        try:
            with csv_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    name = r.get("filename") or r.get("file") or ""
                    if name:
                        seen.add(name)
        except Exception:
            pass
    return seen


def process_once(transcriber: Transcriber, move_on_success: bool = True):
    # Ensure dirs exist
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_CSV.parent.mkdir(parents=True, exist_ok=True)

    # Ensure header exists
    if not METADATA_CSV.exists():
        with METADATA_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "filename",
                    "transcript",
                    "duration_seconds",
                    "speaker",
                    "emotion",
                    "quality",
                ]
            )

    seen = read_seen_filenames(METADATA_CSV)

    for wav in sorted(AUDIO_DIR.glob("*.wav")):
        if wav.name in seen:
            continue
        logger.info(f"Transcribing: {wav}")
        try:
            res = transcriber.transcribe_file(wav)
            if isinstance(res, dict):
                text = res.get("text", "")
                res.get("language", "")
                res.get("confidence", 0.0)
                duration = res.get("duration", None)
            else:
                text = str(res)
                duration = None
        except Exception as e:
            logger.error(f"Failed to transcribe {wav}: {e}")
            continue

        # Append to CSV: filename,transcript,duration_seconds,speaker,emotion,quality
        row = [
            wav.name,
            text.replace("\n", " ").strip(),
            duration or "",
            "target_speaker",
            "",
            "high",
        ]
        atomic_append_csv(METADATA_CSV, row)
        logger.info(f"Appended transcription for {wav.name} to {METADATA_CSV}")

        # Move processed file to processed/ to avoid reprocessing
        if move_on_success:
            processed_dir = AUDIO_DIR.parent / "processed"
            processed_dir.mkdir(parents=True, exist_ok=True)
            try:
                wav.replace(processed_dir / wav.name)
            except Exception as e:
                logger.warning(f"Could not move {wav.name}: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once", action="store_true", help="Process the current queue and exit"
    )
    parser.add_argument("--poll-interval", type=float, default=POLL_INTERVAL)
    args = parser.parse_args()

    transcriber = Transcriber()

    if args.once:
        process_once(transcriber)
        return

    while True:
        process_once(transcriber)
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    main()

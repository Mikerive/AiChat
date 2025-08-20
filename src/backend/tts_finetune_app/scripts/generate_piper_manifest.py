#!/usr/bin/env python3
"""
Generate Piper-compatible manifests from processed clips.

This script:
- Reads processed clips from backend/tts_finetune_app/training_data/processed/
- Validates audio (mono, required sample rate)
- Optionally resamples using ffmpeg
- Produces ljspeech CSV and/or Piper dataset.jsonl
- Can copy validated audio into the output dataset folder
"""
from pathlib import Path
import argparse
import csv
import json
import logging
import soundfile as sf
import subprocess
import tempfile
import shutil
import librosa

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from constants.paths import TTS_TRAINING_PROCESSED, TTS_PIPER_DATASET, ensure_dirs

DEFAULT_PROCESSED = TTS_TRAINING_PROCESSED
DEFAULT_OUTPUT = TTS_PIPER_DATASET

# Ensure default dirs exist when script runs
ensure_dirs(DEFAULT_PROCESSED, DEFAULT_OUTPUT)


def probe_audio(path: Path):
    try:
        info = sf.info(str(path))
        return info.samplerate, info.channels, info.subtype
    except Exception as e:
        logger.error(f"probe failed {path}: {e}")
        return None, None, None


def resample_with_ffmpeg(src: Path, dst: Path, sample_rate: int):
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(src), "-ac", "1", "-ar", str(sample_rate), "-sample_fmt", "s16", str(dst)]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def validate_or_resample(path: Path, required_sr: int, resample: bool):
    sr, ch, st = probe_audio(path)
    if sr == required_sr and ch == 1:
        return path
    if not resample:
        logger.warning(f"{path} invalid (sr={sr},ch={ch}) and resample disabled")
        return None
    tmp = Path(tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name)
    try:
        resample_with_ffmpeg(path, tmp, required_sr)
        return tmp
    except Exception as e:
        logger.error(f"resample failed for {path}: {e}")
        return None


def read_transcripts(metadata_csv: Path):
    mapping = {}
    if not metadata_csv.exists():
        return mapping
    try:
        with metadata_csv.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fname = row.get("filename") or ""
                text = row.get("transcript") or ""
                if fname:
                    mapping[fname] = text
    except Exception as e:
        logger.warning(f"read transcripts failed: {e}")
    return mapping


def main():
    parser = argparse.ArgumentParser(description="Generate Piper manifest files from processed clips")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_PROCESSED, help="Processed clips directory (wav files)")
    parser.add_argument("--metadata-csv", type=Path, default=DEFAULT_PROCESSED.parent / "metadata.csv", help="CSV with transcripts (filename,transcript,...)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT, help="Output directory for Piper dataset/manifest")
    parser.add_argument("--sample-rate", type=int, default=22050, help="Required sample rate for Piper dataset (22050 or 16000)")
    parser.add_argument("--format", choices=["ljspeech", "jsonl", "both"], default="both", help="Which manifest format(s) to generate")
    parser.add_argument("--resample", action="store_true", help="Resample/convert files that do not meet specs using ffmpeg")
    parser.add_argument("--copy-audio", action="store_true", help="Copy validated audio files into the output-dir/wavs/ (recommended)")
    args = parser.parse_args()

    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir
    required_sr = args.sample_rate
    metadata_csv: Path = args.metadata_csv

    if not input_dir.exists():
        logger.error(f"Input dir does not exist: {input_dir}")
        return

    transcripts = read_transcripts(metadata_csv)
    wavs = sorted(input_dir.glob("*.wav"))

    if not wavs:
        logger.warning(f"No wav files found in {input_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    wav_out_dir = output_dir / "wavs"
    if args.copy_audio:
        wav_out_dir.mkdir(parents=True, exist_ok=True)

    ljspeech_rows = []
    jsonl_lines = []
    temp_files_to_cleanup = []

    for wav in wavs:
        validated = validate_or_resample(wav, required_sr, resample=args.resample)
        if validated is None:
            logger.info(f"Skipping {wav} (invalid and not resampled)")
            continue

        # If we resampled into a temp file, remember to cleanup
        if validated.resolve() != wav.resolve():
            temp_files_to_cleanup.append(validated)

        # Determine destination path (either copy into output wavs or use relative path)
        if args.copy_audio:
            dest = wav_out_dir / wav.name
            shutil.copy2(str(validated), str(dest))
            audio_ref = Path("wavs") / wav.name
        else:
            # Use absolute path for simplicity
            audio_ref = wav.resolve()

        # Get transcript (prefer metadata CSV)
        transcript = transcripts.get(wav.name, "")
        if not transcript:
            # try to look for per-clip .json in same dir
            meta_json = wav.with_suffix(".json")
            if meta_json.exists():
                try:
                    with meta_json.open("r", encoding="utf-8") as f:
                        j = json.load(f)
                        transcript = j.get("transcript", j.get("text", ""))
                except Exception:
                    pass

        # Duration
        try:
            y, sr = librosa.load(str(validated), sr=required_sr, mono=True)
            duration = float(len(y) / sr)
        except Exception:
            duration = None

        # Build rows
        if args.format in ("ljspeech", "both"):
            ljspeech_rows.append((str(audio_ref), transcript))

        if args.format in ("jsonl", "both"):
            line = {
                "audio_path": str(audio_ref),
                "text": transcript,
                "duration": duration,
                "speaker": "target_speaker"
            }
            jsonl_lines.append(line)

    # Write outputs
    if args.format in ("ljspeech", "both"):
        ljspeech_path = output_dir / "ljspeech.csv"
        with ljspeech_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="|")
            for r in ljspeech_rows:
                writer.writerow(r)
        logger.info(f"Wrote ljspeech CSV: {ljspeech_path}")

    if args.format in ("jsonl", "both"):
        jsonl_path = output_dir / "dataset.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for obj in jsonl_lines:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        logger.info(f"Wrote dataset jsonl: {jsonl_path}")

    # Cleanup temp files
    for t in temp_files_to_cleanup:
        try:
            Path(t).unlink(missing_ok=True)
        except Exception:
            pass

    logger.info("Manifest generation complete.")


if __name__ == "__main__":
    main()
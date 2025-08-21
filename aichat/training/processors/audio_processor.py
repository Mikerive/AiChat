"""
Enhanced AudioProcessor refactored into processors package.

This file is a direct migration of the previous
backend/tts_finetune_app/audio_processor.py implementation into
backend/tts_finetune_app/processors for cleaner package layout.
"""

import json
import logging
import math
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from aichat.constants.paths import TTS_TRAINING_DIR, ensure_dirs

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TrainingConfig:
    """Minimal config for audio processing. Can be extended or passed in."""

    sample_rate: int = 22050
    min_audio_length: float = 3.0
    max_audio_length: float = 30.0
    training_data_dir: str = str(TTS_TRAINING_DIR)
    frame_ms: float = 30.0
    hop_ms: float = 10.0
    initial_factor: float = 0.5
    min_factor: float = 0.05
    factor_step: float = 0.1


def atomic_write(path: Path, data: bytes):
    """
    Atomic write of bytes to path using a temp file in same directory then replace.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=str(path.parent)) as tmp:
        tmp.write(data)
        tmp.flush()
        tmp_name = Path(tmp.name)
    tmp_name.replace(path)


def atomic_write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(path.parent), encoding="utf-8"
    ) as tmp:
        tmp.write(json.dumps(obj, indent=2))
        tmp.flush()
        tmp_name = Path(tmp.name)
    tmp_name.replace(path)


def compute_sha256(path: Path) -> str:
    h = __import__("hashlib").sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class AudioProcessor:
    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self.base_dir = Path(self.config.training_data_dir)
        self.raw_dir = self.base_dir / "raw"
        self.vocals_dir = self.base_dir / "vocals"
        self.audio_dir = self.base_dir / "audio"
        self.checkpoints_dir = self.base_dir / "checkpoints"
        # Ensure dirs exist
        ensure_dirs(self.raw_dir, self.vocals_dir, self.audio_dir, self.checkpoints_dir)
        logger.info(f"AudioProcessor initialized (training_data_dir={self.base_dir})")

    def load_audio(self, audio_path: Path) -> Tuple[np.ndarray, int]:
        """Load audio into numpy mono array at configured sample rate."""
        audio, sr = librosa.load(str(audio_path), sr=self.config.sample_rate, mono=True)
        return audio, sr

    def convert_video_to_wav(self, input_path: Path, output_path: Path) -> Path:
        """Convert video/audio to mono WAV at configured sample rate using ffmpeg."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(self.config.sample_rate),
            str(output_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Converted {input_path} -> {output_path}")
        return output_path

    def separate_sources(self, audio_path: Path) -> Dict[str, Optional[Path]]:
        """
        Attempt to separate vocals using spleeter (2stems).
        Returns dict: {'vocals': Path or None, 'accompaniment': Path or None}
        Falls back to returning original audio as 'vocals' if spleeter not available.
        """
        out_dir = self.vocals_dir / audio_path.stem
        stems = {"vocals": None, "accompaniment": None}
        try:
            cmd = ["spleeter", "separate", "-o", str(self.vocals_dir), str(audio_path)]
            subprocess.run(
                cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            vocals = out_dir / "vocals.wav"
            accomp = out_dir / "accompaniment.wav"
            if vocals.exists():
                stems["vocals"] = vocals
            if accomp.exists():
                stems["accompaniment"] = accomp
            if stems["vocals"] or stems["accompaniment"]:
                logger.info(f"Spleeter separation succeeded: {audio_path}")
                return stems
        except FileNotFoundError:
            logger.info("spleeter not found - skipping source separation")
        except Exception as e:
            logger.warning(f"Spleeter separation failed: {e}")

        stems["vocals"] = audio_path
        stems["accompaniment"] = None
        return stems

    def _frame_rms(
        self, audio: np.ndarray, frame_length: int = 2048, hop_length: int = 512
    ) -> np.ndarray:
        return librosa.feature.rms(
            y=audio, frame_length=frame_length, hop_length=hop_length
        )[0]

    def split_on_silence_by_deviation(
        self,
        audio: np.ndarray,
        sr: int,
        max_segment_seconds: float,
        initial_factor: float = None,
        min_factor: float = None,
        factor_step: float = None,
    ) -> List[Tuple[float, float]]:
        """
        Split audio into segments by searching for silent regions using RMS energy deviation.
        This mirrors the recursive approach described in project docs: lower factor until oversized segments are split.
        Returns list of (start_sec, end_sec)
        """
        initial_factor = (
            initial_factor if initial_factor is not None else self.config.initial_factor
        )
        min_factor = min_factor if min_factor is not None else self.config.min_factor
        factor_step = (
            factor_step if factor_step is not None else self.config.factor_step
        )

        # frame sizes based on config
        frame_length = int((self.config.frame_ms / 1000.0) * sr)
        hop_length = int((self.config.hop_ms / 1000.0) * sr)
        frame_length = max(frame_length, 256)
        hop_length = max(hop_length, 256)

        rms = self._frame_rms(audio, frame_length=frame_length, hop_length=hop_length)
        times = librosa.frames_to_time(
            np.arange(len(rms)), sr=sr, hop_length=hop_length, n_fft=frame_length
        )

        mean = float(np.mean(rms)) if len(rms) else 0.0
        float(np.std(rms)) if len(rms) else 1e-6

        def find_silence_bounds(factor: float):
            thresh = mean * factor
            silent = rms < thresh
            bounds = []
            start = None
            for i, s in enumerate(silent):
                if s and start is None:
                    start = i
                elif (not s) and start is not None:
                    bounds.append((start, i))
                    start = None
            if start is not None:
                bounds.append((start, len(rms)))
            time_bounds = [(times[s], times[e]) for s, e in bounds]
            return time_bounds

        def split_at_midpoints(boundaries, duration):
            if not boundaries:
                return [(0.0, duration)]
            split_times = [(s + e) / 2.0 for s, e in boundaries]
            split_times = [0.0] + split_times + [duration]
            segments = []
            for i in range(len(split_times) - 1):
                a = split_times[i]
                b = split_times[i + 1]
                if b - a >= 0.01:
                    segments.append((a, b))
            return segments

        audio_duration = len(audio) / sr

        def recursive_split(
            factor: float, segments_to_check: List[Tuple[float, float]]
        ) -> List[Tuple[float, float]]:
            new_segments = []
            for seg in segments_to_check:
                seg_start, seg_end = seg
                seg_len = seg_end - seg_start
                if seg_len <= max_segment_seconds:
                    new_segments.append(seg)
                    continue

                # analyze sub audio
                s_sample = int(seg_start * sr)
                e_sample = min(int(seg_end * sr), len(audio))
                sub_audio = audio[s_sample:e_sample]
                sub_rms = self._frame_rms(
                    sub_audio, frame_length=frame_length, hop_length=hop_length
                )
                if len(sub_rms) < 3 or factor <= min_factor:
                    # fallback: uniform chunking
                    chunk_count = math.ceil(seg_len / max_segment_seconds)
                    for i in range(chunk_count):
                        a = seg_start + i * max_segment_seconds
                        b = min(seg_start + (i + 1) * max_segment_seconds, seg_end)
                        new_segments.append((a, b))
                    continue

                sub_times = librosa.frames_to_time(
                    np.arange(len(sub_rms)),
                    sr=sr,
                    hop_length=hop_length,
                    n_fft=frame_length,
                )
                sub_mean = float(np.mean(sub_rms))
                sub_thresh = sub_mean * factor
                silent = sub_rms < sub_thresh
                bounds = []
                sidx = None
                for i, is_s in enumerate(silent):
                    if is_s and sidx is None:
                        sidx = i
                    elif (not is_s) and sidx is not None:
                        bounds.append((sidx, i))
                        sidx = None
                if sidx is not None:
                    bounds.append((sidx, len(sub_rms)))
                time_bounds = [(sub_times[s], sub_times[e]) for s, e in bounds]

                if not time_bounds:
                    # lower factor and retry
                    new_segments.extend(
                        recursive_split(max(min_factor, factor - factor_step), [seg])
                    )
                else:
                    # convert to global times
                    global_bounds = [
                        (seg_start + s, seg_start + e) for s, e in time_bounds
                    ]
                    segments_created = split_at_midpoints(global_bounds, seg_end)
                    for s_abs, e_abs in segments_created:
                        a_abs = max(seg_start, s_abs)
                        b_abs = min(seg_end, e_abs)
                        if b_abs - a_abs > 0.01:
                            if b_abs - a_abs > max_segment_seconds:
                                new_segments.extend(
                                    recursive_split(
                                        max(min_factor, factor - factor_step),
                                        [(a_abs, b_abs)],
                                    )
                                )
                            else:
                                new_segments.append((a_abs, b_abs))
            return new_segments

        # initial boundaries
        boundaries = find_silence_bounds(initial_factor)
        segments = split_at_midpoints(boundaries, audio_duration)
        final_segments = recursive_split(initial_factor, segments)

        # merge very short segments
        merged = []
        for seg in final_segments:
            if not merged:
                merged.append(seg)
                continue
            prev = merged[-1]
            if seg[1] - seg[0] < 0.5:
                merged[-1] = (prev[0], seg[1])
            else:
                merged.append(seg)

        result = [
            (max(0.0, a), min(audio_duration, b)) for a, b in merged if b - a > 0.05
        ]
        logger.info(f"Split into {len(result)} segments")
        return result

    def _atomic_save_wav(self, out_path: Path, samples: np.ndarray, sr: int):
        """
        Write WAV atomically using a temporary file in the same directory.
        """
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "wb", delete=False, dir=str(out_path.parent)
        ) as tmp:
            tmp_name = Path(tmp.name)
        # Use soundfile to write directly to the temp path
        sf.write(str(tmp_name), samples, sr, subtype="PCM_16")
        tmp_name.replace(out_path)

    def save_segments(
        self,
        audio: np.ndarray,
        sr: int,
        segments: List[Tuple[float, float]],
        base_name: str,
    ) -> List[Path]:
        saved = []
        for i, (start, end) in enumerate(segments):
            s = int(start * sr)
            e = int(end * sr)
            clip = audio[s:e]
            dur = (e - s) / sr
            if dur < self.config.min_audio_length:
                continue
            fname = f"{base_name}_{i:03d}.wav"
            out = self.audio_dir / fname
            try:
                self._atomic_save_wav(out, clip, sr)
                saved.append(out)
            except Exception as e:
                logger.warning(f"Failed to save segment {out}: {e}")
        logger.info(f"Saved {len(saved)} segments to {self.audio_dir}")
        return saved

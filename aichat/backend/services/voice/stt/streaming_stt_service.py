import io
import logging
import os
import tempfile
import time
from collections import deque
from typing import Any, Dict, Optional

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

# Tunables for STD-DEV based VAD
RMS_HISTORY_LENGTH = 30  # number of recent RMS values to track for noise estimate
STD_DEV_MULTIPLIER = 1.8  # multiplier above noise-mean+std to consider voice

# Silero VAD integration (optional, best-effort)
SILERO_AVAILABLE = False
SILERO_MODEL = None
SILERO_UTILS = None
SILERO_SR = 16000  # Silero expects 16k

try:
    import torch

    # Load model and utils via torch.hub; keep this non-fatal if torch not available
    try:
        SILERO_MODEL, SILERO_UTILS = torch.hub.load(
            "snakers4/silero-vad", "silero_vad", force_reload=False
        )
        # SILERO_UTILS should be (get_speech_timestamps, save_audio, read_audio, VADIterator)
        # Some hub variants return tuple(utils) or dict. Normalize below.
        # If SILERO_UTILS is a tuple/list, unpack expected functions
        if isinstance(SILERO_UTILS, (list, tuple)) and len(SILERO_UTILS) >= 1:
            # The first element is typically the utils tuple
            utils_tuple = (
                SILERO_UTILS[0]
                if isinstance(SILERO_UTILS[0], (list, tuple))
                else SILERO_UTILS
            )
            if len(utils_tuple) >= 3:
                get_speech_timestamps = utils_tuple[0]
                # expose via SILERO_UTILS as dict-like for later use
                SILERO_UTILS = {"get_speech_timestamps": get_speech_timestamps}
        elif isinstance(SILERO_UTILS, dict):
            # already dict-like
            pass
        else:
            # try to import helper function name
            # fallback: set SILERO_UTILS to None and rely on model only
            pass

        SILERO_AVAILABLE = True
        logger.info("Silero VAD loaded for improved VAD accuracy")
    except Exception as e:
        SILERO_AVAILABLE = False
        logger.warning(f"Silero VAD not available: {e}")
except Exception:
    SILERO_AVAILABLE = False
    logger.info("torch / silero not installed; running without Silero VAD")

# Sessions stored in memory: ephemeral per running process
# session structure:
# {
#   "chunks": [np.ndarray, ...],
#   "sr": int,
#   "last_voice_time": float,
#   "last_input_time": float
# }
_SESSIONS: Dict[str, Dict[str, Any]] = {}

# Tunables
RMS_VOICE_THRESHOLD = 0.01  # RMS above this considered "voice"
SILENCE_DURATION = 1.0  # seconds of silence to finalize utterance
MIN_UTTERANCE_DURATION = 0.25  # minimum seconds of audio before finalizing

# RNNoise/denoiser integration (best-effort)
RNNOISE_ENABLED = True
RNNOISE_USE_FFMPEG = (
    True  # Prefer ffmpeg arnndn filter if available (no python bindings required)
)

import shutil
import subprocess


def _read_wav_bytes_to_array(wav_bytes: bytes):
    """
    Read WAV/PCM bytes into (np_float32_array, sample_rate)
    Returns mono float32 array.
    """
    data, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    if data is None:
        raise ValueError("No audio data read")
    # Convert to mono if needed
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    return data, sr


def _denoise_via_ffmpeg(wav_bytes: bytes, target_sr: Optional[int] = None) -> bytes:
    """
    Best-effort denoise using ffmpeg's arnndn filter (if ffmpeg compiled with arnndn).
    Returns WAV bytes (raw) or original bytes on failure.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path or not RNNOISE_ENABLED or not RNNOISE_USE_FFMPEG:
        return wav_bytes

    # Create temp files
    in_fd, in_path = tempfile.mkstemp(suffix=".wav", prefix="rn_in_")
    out_fd, out_path = tempfile.mkstemp(suffix=".wav", prefix="rn_out_")
    os.close(in_fd)
    os.close(out_fd)

    try:
        with open(in_path, "wb") as f:
            f.write(wav_bytes)

        cmd = [ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error", "-i", in_path]
        # Use arnndn filter if available; fallback to nothing
        cmd += ["-af", "arnndn", "-ac", "1"]
        if target_sr:
            cmd += ["-ar", str(target_sr)]
        cmd += [out_path]

        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10
        )
        if proc.returncode != 0:
            # ffmpeg failed, return original
            logger.debug(
                f"ffmpeg rnnoise failed: {proc.stderr.decode('utf-8', errors='ignore')}"
            )
            return wav_bytes

        with open(out_path, "rb") as f:
            out_bytes = f.read()

        return out_bytes

    except Exception as e:
        logger.debug(f"RNNoise via ffmpeg error: {e}")
        return wav_bytes

    finally:
        try:
            os.remove(in_path)
        except Exception:
            pass
        try:
            os.remove(out_path)
        except Exception:
            pass


def _denoise_array_if_possible(arr: np.ndarray, sr: int) -> (np.ndarray, int):
    """
    Try to denoise the audio array and return (array, sr).
    This function writes a temporary WAV and calls ffmpeg rnnoise filter if available.
    """
    try:
        # Write to temp WAV
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="rn_tmp_")
        os.close(fd)
        sf.write(path, arr, sr, subtype="PCM_16")
        with open(path, "rb") as f:
            wav_bytes = f.read()
        denoised_bytes = _denoise_via_ffmpeg(wav_bytes, target_sr=sr)
        # Read back
        data, new_sr = _read_wav_bytes_to_array(denoised_bytes)
        return data, new_sr
    except Exception as e:
        logger.debug(f"Denoise failed, using original audio: {e}")
        return arr, sr
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


def _rms(arr: np.ndarray) -> float:
    if arr.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(arr))))


def feed_audio(stream_id: str, wav_bytes: bytes) -> Optional[str]:
    """
    Feed a WAV chunk (bytes) for the given stream_id.
    Uses a rolling RMS history and standard-deviation threshold to determine
    whether the chunk contains voice relative to the recent noise floor.

    Returns a path to a temporary WAV file if the utterance was finalized;
    otherwise returns None.

    This function is synchronous and may be called in a threadpool to avoid blocking asyncio.
    """
    try:
        data, sr = _read_wav_bytes_to_array(wav_bytes)
        # Apply RNNoise denoising (best-effort via ffmpeg arnndn) before VAD processing.
        if RNNOISE_ENABLED:
            try:
                data, sr = _denoise_array_if_possible(data, sr)
            except Exception as e:
                logger.debug(f"RNNoise denoise failed for stream {stream_id}: {e}")
    except Exception as e:
        logger.error(f"Error decoding wav bytes for stream {stream_id}: {e}")
        return None

    now = time.time()
    sess = _SESSIONS.get(stream_id)
    if sess is None:
        sess = {
            "chunks": [],
            "sr": sr,
            "last_voice_time": 0.0,
            "last_voice_sample": 0,
            "last_input_time": now,
            "rms_history": deque(maxlen=RMS_HISTORY_LENGTH),
        }
        _SESSIONS[stream_id] = sess

    # If sample rate differs, prefer the first chunk's SR (simple approach)
    if "sr" not in sess or sess["sr"] is None:
        sess["sr"] = sr

    # Append chunk
    sess["chunks"].append(data)
    sess["last_input_time"] = now

    # Compute RMS for this chunk and update history
    chunk_rms = _rms(data)
    sess["rms_history"].append(chunk_rms)

    # Estimate noise statistics from RMS history.
    # Use median/mean and stddev for robustness.
    rms_vals = (
        np.array(list(sess["rms_history"])) if sess["rms_history"] else np.array([0.0])
    )
    noise_mean = float(np.mean(rms_vals))
    noise_std = float(np.std(rms_vals, ddof=1)) if rms_vals.size > 1 else 0.0

    # Determine voice presence: chunk is voice if its RMS exceeds noise_mean + k * noise_std
    is_voice = False
    threshold = None
    if noise_std > 0:
        threshold = noise_mean + (STD_DEV_MULTIPLIER * noise_std)
        is_voice = chunk_rms >= threshold
    else:
        # fallback to absolute RMS threshold when insufficient history
        threshold = RMS_VOICE_THRESHOLD
        is_voice = chunk_rms >= RMS_VOICE_THRESHOLD

    # Debug logging for VAD decision (elevated to INFO during tests so it's visible)
    logger.info(
        "STT VAD stream=%s chunk_rms=%.6f noise_mean=%.6f noise_std=%.6f threshold=%s is_voice=%s chunks=%d",
        stream_id,
        chunk_rms,
        noise_mean,
        noise_std,
        f"{threshold:.6f}" if isinstance(threshold, float) else str(threshold),
        is_voice,
        len(sess["chunks"]),
    )

    # Update last_voice_sample (audio-based position) when voice detected.
    # Compute total duration so far (in audio time)
    total_samples = sum(arr.shape[0] for arr in sess["chunks"])
    total_duration = total_samples / float(sess["sr"]) if sess["sr"] else 0.0

    if is_voice:
        sess["last_voice_time"] = now
        sess["last_voice_sample"] = total_samples

    # Determine silence length in audio time (seconds since last voice sample)
    samples_since_voice = total_samples - sess.get("last_voice_sample", 0)
    seconds_since_voice_audio = (
        samples_since_voice / float(sess["sr"]) if sess["sr"] else float("inf")
    )

    # Also compute wall-clock silence for diagnostics
    time_since_wall_clock = now - (
        sess["last_voice_time"] if sess["last_voice_time"] else sess["last_input_time"]
    )

    logger.info(
        "STT session stream=%s total_duration=%.3fs seconds_since_voice_audio=%.3fs time_since_wall_clock=%.3fs chunks=%d",
        stream_id,
        total_duration,
        seconds_since_voice_audio,
        time_since_wall_clock,
        len(sess["chunks"]),
    )

    # Finalize when audio-silence exceeds threshold (preferred) and utterance is long enough.
    if (
        seconds_since_voice_audio >= SILENCE_DURATION
        and total_duration >= MIN_UTTERANCE_DURATION
    ):
        # Concatenate and write to a temp WAV file
        try:
            concatenated = (
                np.concatenate(sess["chunks"])
                if len(sess["chunks"]) > 1
                else sess["chunks"][0]
            )
            # Write 16-bit PCM WAV
            fd, path = tempfile.mkstemp(suffix=".wav", prefix=f"stream_{stream_id}_")
            os.close(fd)
            sf.write(path, concatenated, sess["sr"], subtype="PCM_16")
            logger.info(
                f"Finalized utterance for stream {stream_id}, wrote {path} (duration={total_duration:.2f}s) "
                f"[noise_mean={noise_mean:.6f}, noise_std={noise_std:.6f}, chunk_rms={chunk_rms:.6f}]"
            )
            # Clear session
            _SESSIONS.pop(stream_id, None)
            return path
        except Exception as e:
            logger.error(f"Error finalizing utterance for stream {stream_id}: {e}")
            # attempt cleanup
            _SESSIONS.pop(stream_id, None)
            return None

    # Not finalized yet
    return None


def reset_session(stream_id: str):
    """Clear buffered data for a stream (e.g., on disconnect)."""
    _SESSIONS.pop(stream_id, None)


def get_silero_decision(stream_id: str, tail_seconds: float = 6.0):
    """
    Synchronous helper: run Silero VAD on the tail of the buffered audio for a stream.
    Returns a list of speech timestamp dicts (may be empty) or None if Silero unavailable.
    This is synchronous and intended to be run in an executor from async endpoints.
    """
    if not SILERO_AVAILABLE or SILERO_MODEL is None or not SILERO_UTILS:
        return None

    sess = _SESSIONS.get(stream_id)
    if not sess:
        return None

    try:
        concatenated = (
            np.concatenate(sess["chunks"])
            if len(sess["chunks"]) > 1
            else sess["chunks"][0]
        )
        sr = sess["sr"]
        tail_samples = int(min(concatenated.shape[0], int(tail_seconds * sr)))
        tail = concatenated[-tail_samples:]
        # resample if needed
        if sr != SILERO_SR:
            try:
                # simple resample
                src_indices = np.linspace(0, tail.shape[0] - 1, num=tail.shape[0])
                tgt_indices = np.linspace(
                    0, tail.shape[0] - 1, num=int(round(tail_seconds * SILERO_SR))
                )
                tail_rs = np.interp(tgt_indices, src_indices, tail).astype(np.float32)
            except Exception:
                tail_rs = tail
        else:
            tail_rs = tail.astype(np.float32)

        # Prepare input for Silero utils
        get_ts = None
        if isinstance(SILERO_UTILS, dict) and "get_speech_timestamps" in SILERO_UTILS:
            get_ts = SILERO_UTILS["get_speech_timestamps"]
        elif callable(SILERO_UTILS):
            get_ts = SILERO_UTILS

        if not get_ts:
            return None

        # Some wrappers expect torch tensors; attempt to import torch
        try:
            import torch

            audio_tensor = torch.from_numpy(tail_rs)
            speech_timestamps = get_ts(
                audio_tensor, SILERO_MODEL, sampling_rate=SILERO_SR
            )
        except Exception:
            # fallback to numpy
            try:
                speech_timestamps = get_ts(
                    tail_rs, SILERO_MODEL, sampling_rate=SILERO_SR
                )
            except Exception:
                return None

        return speech_timestamps
    except Exception:
        return None


def get_session_info(stream_id: str) -> Optional[Dict[str, Any]]:
    """Return diagnostic info about a session (useful for status endpoints)."""
    sess = _SESSIONS.get(stream_id)
    if not sess:
        return None
    total_samples = sum(arr.shape[0] for arr in sess["chunks"])
    total_duration = total_samples / float(sess["sr"]) if sess["sr"] else 0.0
    return {
        "stream_id": stream_id,
        "chunks": len(sess["chunks"]),
        "sample_rate": sess["sr"],
        "buffered_seconds": total_duration,
        "last_voice_time": sess["last_voice_time"],
        "last_input_time": sess["last_input_time"],
    }

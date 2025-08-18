import sys
import io
import wave
import struct
import math
import time
import tempfile

# Ensure src/ is importable
sys.path.insert(0, "src")

from backend.chat_app.services.streaming_stt_service import feed_audio
from backend.chat_app.services.service_manager import get_whisper_service
import asyncio

def make_wav_bytes(duration_s: float = 0.5, sr: int = 16000, freq: float = 440.0, amplitude: float = 0.3, silent: bool = False) -> bytes:
    n_samples = int(sr * duration_s)
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(n_samples):
            if silent:
                sample = 0.0
            else:
                t = i / float(sr)
                sample = amplitude * math.sin(2.0 * math.pi * freq * t)
            val = int(max(-1.0, min(1.0, sample)) * 32767.0)
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return bio.getvalue()

async def transcribe_path(path: str):
    whisper = get_whisper_service()
    try:
        res = await whisper.transcribe_audio(path)
        return res
    except Exception as e:
        return {"error": str(e)}

def run():
    stream_id = f"transcribe-test-{int(time.time()*1000)}"
    print("stream_id:", stream_id)

    # send 3 voice chunks
    finalized_paths = []
    for i in range(3):
        wav = make_wav_bytes(duration_s=0.5, sr=16000, freq=400.0 + (i*20), amplitude=0.4, silent=False)
        p = feed_audio(stream_id, wav)
        print("voice chunk", i, "->", p)
        if p:
            finalized_paths.append(p)

    # send 3 silence chunks
    for i in range(3):
        silence = make_wav_bytes(duration_s=0.5, sr=16000, silent=True)
        p = feed_audio(stream_id, silence)
        print("silence chunk", i, "->", p)
        if p:
            finalized_paths.append(p)

    print("finalized_paths:", finalized_paths)

    # Transcribe each finalized path
    for p in finalized_paths:
        print("Transcribing:", p)
        result = asyncio.run(transcribe_path(p))
        print("Transcription result:", result)

if __name__ == "__main__":
    run()
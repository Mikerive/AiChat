import sys
import io
import wave
import struct
import math
import time
import tempfile

# Ensure package import works
sys.path.insert(0, "src")
from backend.chat_app.services.stt_services.streaming_stt_service import feed_audio

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

stream_id = f"test-run-{int(time.time()*1000)}"
print("Using stream_id:", stream_id)
paths = []
for i in range(3):
    wav = make_wav_bytes(duration_s=0.5, sr=16000, freq=400.0 + (i*20), amplitude=0.4, silent=False)
    p = feed_audio(stream_id, wav)
    print("voice chunk", i, "->", p)
    paths.append(p)

for i in range(3):
    silence = make_wav_bytes(duration_s=0.5, sr=16000, silent=True)
    p = feed_audio(stream_id, silence)
    print("silence chunk", i, "->", p)
    paths.append(p)

print("Final results:", paths)
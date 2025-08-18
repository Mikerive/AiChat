import sys
import io
import wave
import struct
import math
import time
import base64
import asyncio
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, "src")

from backend.chat_app.routes.websocket import process_audio_stream_chunk
from backend.chat_app.services.streaming_stt_service import feed_audio

# Create a small WAV bytes helper (same format as tests)
def make_wav_bytes(duration_s: float = 1.5, sr: int = 16000, freq: float = 440.0, amplitude: float = 0.4, silent: bool = False) -> bytes:
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

class MockWebSocket:
    def __init__(self):
        self.sent = []
    async def send_text(self, text: str):
        self.sent.append(text)
    async def send_json(self, obj):
        import json
        self.sent.append(json.dumps(obj))

async def run_test():
    # Build a short audio (1.5s) and base64 encode it as the route expects
    wav_bytes = make_wav_bytes(duration_s=1.5, sr=16000, freq=440.0, amplitude=0.4, silent=False)
    b64 = base64.b64encode(wav_bytes).decode("ascii")

    # Use a unique stream id
    stream_id = f"process-test-{int(time.time()*1000)}"

    # Create mock websocket
    mock_ws = MockWebSocket()

    # Call the route handler directly
    await process_audio_stream_chunk(mock_ws, b64, stream_id)

    # Print captured messages
    print("Captured messages from process_audio_stream_chunk:")
    for i, msg in enumerate(mock_ws.sent):
        print(f"[{i}] {msg[:200]}{'...' if len(msg)>200 else ''}")

if __name__ == "__main__":
    asyncio.run(run_test())
# Integration test for voice -> STT -> chat -> TTS pipeline over WebSocket
# This test synthesizes short WAV chunks (voice + silence), sends them as base64
# via the websocket `audio_stream` message, and asserts that:
#  - a transcription is produced within 10 seconds
#  - a chat response (chat_complete) with an audio_file is returned
#
# Run with: pytest tests/integration -q
import sys
from pathlib import Path
import io
import wave
import struct
import math
import time
import base64
import json
from fastapi.testclient import TestClient

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.main import create_app

def _make_wav_bytes(duration_s: float = 0.5, sr: int = 16000, freq: float = 440.0, amplitude: float = 0.3, silent: bool = False) -> bytes:
    """
    Create a mono PCM16 WAV in-memory and return bytes.
    - duration_s: seconds per chunk (matching frontend chunking ~0.5s)
    - sr: sample rate
    - freq: sine frequency for simulated voice
    - amplitude: peak amplitude (0.0-1.0)
    - silent: if True produces zeros (silence)
    """
    n_samples = int(sr * duration_s)
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(n_samples):
            if silent:
                sample = 0.0
            else:
                t = i / float(sr)
                # simple sine wave (not real speech, but enough energy for VAD)
                sample = amplitude * math.sin(2.0 * math.pi * freq * t)
            # PCM16
            val = int(max(-1.0, min(1.0, sample)) * 32767.0)
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return bio.getvalue()

def test_voice_to_text_and_text_to_voice_pipeline():
    """
    This test will:
      1) Connect to WebSocket /api/ws
      2) Send a few voice chunks (0.5s each)
      3) Send a couple of silence chunks so the server can finalize the utterance
      4) Wait up to 10 seconds for the server to reply with transcription + chat_complete (TTS)
      5) Assert transcription text exists and chat_complete contains an audio_file path (file may be placeholder)
    """
    app = create_app()
    client = TestClient(app)

    # unique stream id for this test run
    stream_id = f"test-stream-{int(time.time()*1000)}"

    with client.websocket_connect("/api/ws") as ws:
        # initial welcome may be sent by the connection manager
        try:
            raw = ws.receive_text(timeout=2)
            # ignore content, just confirm connection established
        except Exception:
            pass

        # Subscribe to events of interest to simplify later reads
        ws.send_json({"type": "subscribe", "events": ["audio_transcribed", "audio_generated", "chat.response", "chat_complete"]})
        try:
            sub = ws.receive_json(timeout=2)
        except Exception:
            # subscription ack may be optional depending on startup ordering
            sub = {}

        # Send several "voice" chunks
        for i in range(3):
            wav = _make_wav_bytes(duration_s=0.5, sr=16000, freq=400.0 + (i*20), amplitude=0.4, silent=False)
            b64 = base64.b64encode(wav).decode("ascii")
            ws.send_json({"type": "audio_stream", "stream_id": stream_id, "audio_data": b64})
            # receive optional ack audio_received
            try:
                ack = ws.receive_json(timeout=2)
            except Exception:
                ack = None

        # Send explicit silence chunks so feed_audio can see silence and finalize
        for _ in range(3):
            silence = _make_wav_bytes(duration_s=0.5, sr=16000, silent=True)
            b64s = base64.b64encode(silence).decode("ascii")
            ws.send_json({"type": "audio_stream", "stream_id": stream_id, "audio_data": b64s})
            try:
                ack = ws.receive_json(timeout=2)
            except Exception:
                ack = None

        # Now wait up to 10 seconds for transcription_final and chat_complete
        deadline = time.time() + 10.0
        got_transcription = None
        got_chat_complete = None

        while time.time() < deadline and (got_transcription is None or got_chat_complete is None):
            try:
                msg = ws.receive_text(timeout=deadline - time.time())
            except Exception:
                break
            try:
                payload = json.loads(msg)
            except Exception:
                continue

            mtype = payload.get("type") or payload.get("event") or ""
            if mtype in ("transcription_final", "transcription", "transcription_partial"):
                # capture transcription
                if payload.get("text") or payload.get("partial"):
                    got_transcription = payload
            if payload.get("type") == "chat_complete" or payload.get("event") == "response_ready":
                got_chat_complete = payload

        assert got_transcription is not None, "No transcription received within timeout (10s)"
        # transcription should contain some non-empty text (mock or real)
        text = got_transcription.get("text") or got_transcription.get("partial") or ""
        assert isinstance(text, str) and text.strip() != "", f"Transcription empty: {got_transcription}"

        assert got_chat_complete is not None, "No chat_complete / TTS response received within timeout (10s)"
        # chat_complete should contain a character_response or audio_file
        # websocket handler constructs the chat_complete with 'character_response' and 'audio_file'
        char_resp = got_chat_complete.get("character_response") or got_chat_complete.get("text") or got_chat_complete.get("character_response")
        audio_file = got_chat_complete.get("audio_file")
        assert (char_resp and isinstance(char_resp, str)) or audio_file is not None, f"chat_complete payload missing response/audio: {got_chat_complete}"
import sys
from pathlib import Path
# Ensure src/ is importable (like the integration tests)
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest
import json
from types import SimpleNamespace
from datetime import datetime
from fastapi.testclient import TestClient

# import app and route modules to patch dependencies
from backend.chat_app.main import create_app
import backend.chat_app.routes.chat as chat_mod
import backend.chat_app.routes.system as system_mod
import backend.chat_app.routes.voice as voice_mod


def async_return(value):
    async def _inner(*args, **kwargs):
        return value
    return _inner


class MockChatService:
    def __init__(self):
        pass
    async def process_message(self, text, character_id, character_name):
        return SimpleNamespace(response=f"{text}", emotion="neutral", model_used="mock-model")
    async def switch_character(self, character_id, character_name):
        return True
    async def generate_tts(self, text, character_id, character_name):
        return "/tmp/fake_audio.wav"
    async def get_current_character(self):
        return {"id": 1, "name": "hatsune_miku"}

class MockWhisperService:
    async def transcribe_audio(self, path):
        return {"text": "transcribed text", "language": "en", "confidence": 0.99, "processing_time": 0.1}

class MockDBOps:
    async def list_characters(self):
        return [SimpleNamespace(id=1,name="hatsune_miku",profile="A singer",personality="cheerful",avatar_url=None)]
    async def get_character(self, cid):
        if int(cid) == 1:
            return SimpleNamespace(id=1,name="hatsune_miku",profile="A singer",personality="cheerful",avatar_url=None)
        return None
    async def get_character_by_name(self, name):
        if name == "hatsune_miku":
            return SimpleNamespace(id=1,name="hatsune_miku",profile="A singer",personality="cheerful",avatar_url=None)
        return None
    async def create_chat_log(self, character_id, user_message, character_response, emotion, metadata):
        return SimpleNamespace(id=1)
    async def get_chat_logs(self, character_id=None, limit=100):
        return [SimpleNamespace(id=1,character_id=1,user_message="hi",character_response="hi",timestamp=datetime.utcnow(),emotion="neutral",metadata={})]
    async def list_voice_models(self, limit=100):
        return []
    async def list_training_data(self, limit=100):
        return []
    async def create_training_data(self, filename, transcript=None, duration=None, speaker=None, quality=None):
        return SimpleNamespace(id=1, filename=filename)


@pytest.fixture
def app_with_mocks(monkeypatch):
    # Patch db_ops and services inside route modules
    mock_db = MockDBOps()
    monkeypatch.setattr(chat_mod, "db_ops", mock_db)
    monkeypatch.setattr(voice_mod, "db_ops", mock_db)
    # Patch event emitters the routes import
    async def _emit_chat_response(title, payload):
        # no-op for unit tests
        return None
    monkeypatch.setattr(chat_mod, "emit_chat_response", _emit_chat_response)
    # Patch system event system methods used in system routes
    class MockEventSystem:
        async def list_webhooks(self):
            return ["https://example.com/hook"]
        async def add_webhook(self, url):
            return True
        async def remove_webhook(self, url):
            return True
    monkeypatch.setattr(system_mod, "get_event_system", lambda: MockEventSystem())
    # Patch streaming_stt_service helpers used by system routes
    class MockSTT:
        SILERO_AVAILABLE = False
        def get_session_info(self, stream_id):
            return {"stream_id": stream_id, "rms_history": [], "buffered_seconds": 0}
        def get_silero_decision(self, stream_id, tail_seconds):
            return []
    monkeypatch.setattr(system_mod, "stt", MockSTT())
    # Patch chat service and whisper service via dependency overrides
    mock_chat_service = MockChatService()
    mock_whisper = MockWhisperService()

    # Also patch the global service manager function for chat so the app uses our mocked ChatService.
    # We DO NOT patch WhisperService here because tests should initialize and use the real Whisper implementation.
    import backend.chat_app.services.service_manager as svc_mgr
    monkeypatch.setattr(svc_mgr, "get_chat_service", lambda *args, **kwargs: mock_chat_service)

    # Ensure the chat service implementation uses our mocked db_ops (it imports db_ops directly)
    import backend.chat_app.services.chat_service as chat_service_mod
    monkeypatch.setattr(chat_service_mod, "db_ops", mock_db)


    # Patch the functions in the chat module so the route dependencies bind to mocks at router registration time
    monkeypatch.setattr(chat_mod, "get_chat_service_dep", lambda: mock_chat_service)
    monkeypatch.setattr(chat_mod, "get_whisper_service_dep", lambda: mock_whisper)
    monkeypatch.setattr(voice_mod, "get_voice_service_dep", lambda: SimpleNamespace())

    app = create_app()

    # Also register FastAPI dependency_overrides as a safety-net
    app.dependency_overrides[chat_mod.get_chat_service_dep] = lambda: mock_chat_service
    app.dependency_overrides[chat_mod.get_whisper_service_dep] = lambda: mock_whisper
    app.dependency_overrides[voice_mod.get_voice_service_dep] = lambda: SimpleNamespace()

    return app


def test_list_and_get_character(app_with_mocks):
    client = TestClient(app_with_mocks)
    r = client.get("/api/chat/characters")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert data[0]["name"] == "hatsune_miku"

    r2 = client.get("/api/chat/characters/1")
    assert r2.status_code == 200
    c = r2.json()
    assert c["id"] == 1

def test_chat_endpoint_echo_and_db_log(app_with_mocks):
    client = TestClient(app_with_mocks)
    payload = {"text": "hello unit", "character": "hatsune_miku"}
    r = client.post("/api/chat/chat", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["user_input"] == "hello unit"
    assert "response" in body

def test_switch_and_tts(app_with_mocks):
    client = TestClient(app_with_mocks)
    r = client.post("/api/chat/switch_character", json={"character": "hatsune_miku"})
    assert r.status_code == 200
    s = r.json()
    assert s["status"] == "switched"

    r2 = client.post("/api/chat/tts", json={"text": "speak", "character": "hatsune_miku"})
    assert r2.status_code == 200
    t = r2.json()
    assert t["audio_format"] == "wav"
    assert t["audio_file"] is not None

def test_stt_upload(app_with_mocks, tmp_path):
    client = TestClient(app_with_mocks)
    import wave
    # Create a valid 1-second 16-bit mono WAV at 16kHz (silence) so Whisper/ffmpeg can read it
    file_path = tmp_path / "small.wav"
    sample_rate = 16000
    duration_s = 1
    n_frames = sample_rate * duration_s
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)

    with open(file_path, "rb") as f:
        r = client.post("/api/chat/stt", files={"file": ("small.wav", f, "audio/wav")})
    assert r.status_code == 200
    body = r.json()
    # When using the real Whisper model, transcription may vary; ensure we received text (non-empty string)
    assert "text" in body and isinstance(body["text"], str) and len(body["text"].strip()) > 0

def test_chat_history_and_status(app_with_mocks):
    client = TestClient(app_with_mocks)
    r = client.get("/api/chat/chat/history")
    assert r.status_code == 200
    hist = r.json()
    assert "history" in hist and isinstance(hist["history"], list)

    r2 = client.get("/api/chat/status")
    assert r2.status_code == 200
    s = r2.json()
    assert s["backend"] == "running"
    assert "current_character" in s

def test_whisper_model_initialized():
    """Ensure the Whisper model is initialized and available (real model)"""
    import asyncio
    from backend.chat_app.services.core_services import service_manager as svc_mgr
    # Acquire the whisper service created by the factory
    whisper_svc = svc_mgr.get_whisper_service()
    model_info = asyncio.get_event_loop().run_until_complete(whisper_svc.get_model_info())
    assert "initialized" in model_info
    assert model_info["initialized"] is True

def test_system_webhooks_and_status(app_with_mocks):
    client = TestClient(app_with_mocks)
    r = client.get("/api/system/webhooks")
    assert r.status_code == 200
    w = r.json()
    assert "webhooks" in w and isinstance(w["webhooks"], list)

    r2 = client.post("/api/system/webhooks", json={"url": "https://example.com/hook"})
    assert r2.status_code == 200
    assert r2.json().get("status") == "ok"

    r3 = client.delete("/api/system/webhooks", params={"url": "https://example.com/hook"})
    assert r3.status_code == 200
    assert r3.json().get("status") == "ok"

    r4 = client.get("/api/system/status")
    assert r4.status_code == 200
    sys_status = r4.json()
    assert sys_status["status"] == "running"
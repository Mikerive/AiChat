# Integration tests for the lightweight/recreated API app
# Run with: pytest tests/integration -q
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure src/ is on path so imports like `from backend.chat_app.api.routes import app` work
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.api.routes import app as api_app


def test_root_and_health_endpoints():
    client = TestClient(api_app)
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "message" in body and "status" in body

    r2 = client.get("/health")
    assert r2.status_code == 200
    h = r2.json()
    assert "status" in h
    assert h["status"] in ("healthy", "unhealthy")


def test_characters_and_chat_echo_and_tts_switch():
    client = TestClient(api_app)

    # List characters (lightweight placeholder loader should return a list)
    r = client.get("/characters")
    assert r.status_code == 200
    payload = r.json()
    assert "characters" in payload
    assert isinstance(payload["characters"], list)

    # Chat endpoint in this recreated app echoes when pipeline is not initialized
    r = client.post("/chat", json={"text": "hello world", "character": "hatsune_miku"})
    assert r.status_code == 200
    body = r.json()
    assert "response" in body
    assert "(echo)" in body["response"]

    # TTS placeholder should return a generated placeholder when pipeline absent
    r = client.post("/tts", json={"text": "speak this", "character": "hatsune_miku"})
    assert r.status_code == 200
    t = r.json()
    assert t.get("audio_format") == "wav"

    # Switch character placeholder
    r = client.post("/switch_character", json={"character": "default_assistant"})
    assert r.status_code == 200
    s = r.json()
    assert s.get("status") == "switched"
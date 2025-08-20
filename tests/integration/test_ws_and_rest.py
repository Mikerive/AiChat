# Integration tests for the full FastAPI app (create_app)
# Run with: pytest tests/integration -q
import sys
from pathlib import Path
import json
import time
from fastapi.testclient import TestClient

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.main import create_app

def test_app_root_and_health():
    app = create_app()
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    j = r.json()
    assert "message" in j and j["status"] == "running"

    r2 = client.get("/health")
    assert r2.status_code == 200
    h = r2.json()
    assert "status" in h

def test_websocket_connect_subscribe_and_ping_and_chat():
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/api/ws") as ws:
        # The connection manager sends a welcome message on connect
        msg = ws.receive_text()
        try:
            parsed = json.loads(msg)
        except Exception:
            parsed = {"raw": msg}
        # welcome message should at least indicate a connection
        assert parsed.get("type") in ("connection", None) or "connected" in str(parsed)

        # Subscribe to a couple of events
        ws.send_json({"type": "subscribe", "events": ["audio_transcribed", "chat.response"]})
        sub_resp = ws.receive_json(timeout=5)
        assert sub_resp.get("type") == "subscription"
        assert sub_resp.get("event") == "subscribed"
        assert "events" in sub_resp

        # Send a ping and expect a pong
        ws.send_json({"type": "ping"})
        pong = ws.receive_json(timeout=5)
        assert pong.get("type") == "pong"

        # Send a simple chat message and expect an echoed chat response payload
        ws.send_json({"type": "chat", "text": "hello from test", "character": "hatsune_miku"})
        chat_msg = ws.receive_json(timeout=5)
        # chat handler sends back a message with type "chat"
        assert chat_msg.get("type") == "chat"
        assert "text" in chat_msg and chat_msg["text"] == "hello from test"
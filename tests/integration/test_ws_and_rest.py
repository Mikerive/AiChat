# Integration tests for WebSocket and REST API coordination
# Tests the integration between WebSocket real-time communication and REST endpoints
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


def test_websocket_and_rest_coordination():
    """Test that WebSocket events are properly coordinated with REST API calls"""
    app = create_app()
    client = TestClient(app)

    # First ensure REST endpoints are working
    rest_health = client.get("/health")
    assert rest_health.status_code == 200

    # Then test WebSocket connectivity and event coordination
    with client.websocket_connect("/api/ws") as ws:
        # Receive welcome message
        welcome_msg = ws.receive_text(timeout=5)
        try:
            parsed_welcome = json.loads(welcome_msg)
        except Exception:
            parsed_welcome = {"raw": welcome_msg}

        # WebSocket should be properly initialized
        assert (
            "connected" in str(parsed_welcome)
            or parsed_welcome.get("type") == "connection"
        )

        # Test event subscription system
        ws.send_json(
            {"type": "subscribe", "events": ["system.status", "chat.response"]}
        )
        sub_resp = ws.receive_json(timeout=5)
        assert sub_resp.get("type") == "subscription"
        assert "events" in sub_resp

        # Test ping/pong mechanism
        ws.send_json({"type": "ping"})
        pong = ws.receive_json(timeout=5)
        assert pong.get("type") == "pong"


def test_cross_app_event_system():
    """Test that events can be sent between different parts of the application"""
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/api/ws") as ws:
        # Subscribe to chat events
        ws.send_json(
            {"type": "subscribe", "events": ["chat.response", "system.status"]}
        )
        ws.receive_json(timeout=5)  # subscription ack

        # Send a chat message via WebSocket
        ws.send_json(
            {"type": "chat", "text": "integration test", "character": "hatsune_miku"}
        )

        # Should receive the chat response
        chat_response = ws.receive_json(timeout=10)
        assert chat_response.get("type") == "chat"
        assert "text" in chat_response


def test_rest_and_websocket_state_consistency():
    """Test that state is consistent between REST API and WebSocket connections"""
    app = create_app()
    client = TestClient(app)

    # Get initial system status via REST
    rest_status = client.get("/api/system/status")
    assert rest_status.status_code == 200
    rest_data = rest_status.json()

    # Connect to WebSocket and check status consistency
    with client.websocket_connect("/api/ws") as ws:
        ws.send_json({"type": "subscribe", "events": ["system.status"]})
        ws.receive_json(timeout=5)  # subscription ack

        # Request status via WebSocket
        ws.send_json({"type": "get_status"})
        ws_status = ws.receive_json(timeout=5)

        # Both should indicate the system is running
        assert rest_data["status"] == "running"
        # WebSocket response might be in different format, but should indicate system is operational
        assert "status" in str(ws_status) or "running" in str(ws_status)


def test_event_system_webhook_integration():
    """Test that the event system can properly handle webhook configurations"""
    app = create_app()
    client = TestClient(app)

    # Test webhook management via REST API
    webhook_url = "https://example.com/test-webhook"

    # Add webhook via REST
    add_response = client.post("/api/system/webhooks", json={"url": webhook_url})
    if add_response.status_code == 200:
        # List webhooks to confirm
        list_response = client.get("/api/system/webhooks")
        assert list_response.status_code == 200
        webhooks_data = list_response.json()
        assert "webhooks" in webhooks_data

        # Remove webhook
        remove_response = client.delete(
            "/api/system/webhooks", params={"url": webhook_url}
        )
        # Should either succeed or indicate webhook wasn't found
        assert remove_response.status_code in [200, 404]


def test_multi_service_integration():
    """Test integration between chat_app and other potential services"""
    app = create_app()
    client = TestClient(app)

    # Test that the main app can handle requests that might involve multiple services
    health_response = client.get("/health")
    assert health_response.status_code == 200

    # Test character endpoint (integrates database and character management)
    chars_response = client.get("/api/chat/characters")
    assert chars_response.status_code == 200

    # Test system status (integrates multiple service statuses)
    status_response = client.get("/api/system/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert "services" in status_data or "status" in status_data

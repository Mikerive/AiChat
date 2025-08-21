# Integration tests for cross-application communication
# This tests communication between the lightweight API and the main chat_app
# Run with: pytest tests/integration -q
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure src/ is on path
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.api.routes import app as lightweight_api_app
from backend.chat_app.main import create_app as create_main_app


def test_lightweight_api_health_check():
    """Test that the lightweight API is accessible and responds correctly"""
    client = TestClient(lightweight_api_app)
    r = client.get("/health")
    assert r.status_code == 200
    h = r.json()
    assert "status" in h
    assert h["status"] in ("healthy", "unhealthy")


def test_main_app_health_check():
    """Test that the main chat app is accessible and responds correctly"""
    main_app = create_main_app()
    client = TestClient(main_app)
    r = client.get("/health")
    assert r.status_code == 200
    h = r.json()
    assert "status" in h


def test_lightweight_api_fallback_behavior():
    """Test that the lightweight API provides fallback behavior when main services are unavailable"""
    client = TestClient(lightweight_api_app)

    # Chat should echo when full pipeline unavailable
    r = client.post("/chat", json={"text": "hello world", "character": "hatsune_miku"})
    assert r.status_code == 200
    body = r.json()
    assert "response" in body
    # Should indicate it's a fallback/echo response
    assert (
        "(echo)" in body["response"] or "placeholder" in body.get("status", "").lower()
    )

    # TTS should provide placeholder when main TTS unavailable
    r = client.post("/tts", json={"text": "speak this", "character": "hatsune_miku"})
    assert r.status_code == 200
    t = r.json()
    assert t.get("audio_format") == "wav"


def test_app_api_compatibility():
    """Test that both APIs use compatible response formats"""
    lightweight_client = TestClient(lightweight_api_app)
    main_app = create_main_app()
    main_client = TestClient(main_app)

    # Test root endpoint compatibility
    lightweight_root = lightweight_client.get("/")
    main_root = main_client.get("/")

    assert lightweight_root.status_code == 200
    assert main_root.status_code == 200

    # Both should have similar response structure
    lightweight_data = lightweight_root.json()
    main_data = main_root.json()

    # Both should have status fields
    assert "status" in lightweight_data
    assert "status" in main_data


def test_character_listing_compatibility():
    """Test that character listing works across both apps"""
    lightweight_client = TestClient(lightweight_api_app)
    main_app = create_main_app()
    main_client = TestClient(main_app)

    # Lightweight API characters endpoint
    r1 = lightweight_client.get("/characters")
    assert r1.status_code == 200
    lightweight_chars = r1.json()
    assert "characters" in lightweight_chars
    assert isinstance(lightweight_chars["characters"], list)

    # Main app characters endpoint
    r2 = main_client.get("/api/chat/characters")
    assert r2.status_code == 200
    main_chars = r2.json()
    assert isinstance(main_chars, list)

    # Both should provide character data (even if different sources)

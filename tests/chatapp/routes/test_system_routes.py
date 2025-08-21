import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from backend.chat_app.routes.system import router
from fastapi import FastAPI


@pytest.fixture
def mock_event_system():
    mock_system = AsyncMock()
    mock_system.list_webhooks.return_value = [
        "https://example.com/hook1",
        "https://example.com/hook2",
    ]
    mock_system.add_webhook.return_value = True
    mock_system.remove_webhook.return_value = True
    return mock_system


@pytest.fixture
def mock_streaming_stt():
    mock_stt = MagicMock()
    mock_stt.SILERO_AVAILABLE = True
    mock_stt.get_session_info.return_value = {
        "stream_id": "test_stream",
        "rms_history": [0.1, 0.2, 0.15],
        "buffered_seconds": 2.5,
    }
    mock_stt.get_silero_decision.return_value = [
        {"decision": "speech", "start": 0.0, "end": 1.0},
        {"decision": "silence", "start": 1.0, "end": 2.0},
    ]
    return mock_stt


@pytest.fixture
def app_with_mocks(mock_event_system, mock_streaming_stt):
    app = FastAPI()

    with patch(
        "backend.chat_app.routes.system.get_event_system",
        return_value=mock_event_system,
    ), patch("backend.chat_app.routes.system.stt", mock_streaming_stt):

        app.include_router(router, prefix="/api/system")
        yield app


def test_get_system_status(app_with_mocks):
    client = TestClient(app_with_mocks)

    response = client.get("/api/system/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "uptime" in data
    assert "memory_usage" in data
    assert data["services"]["event_system"] == "running"


def test_list_webhooks(app_with_mocks, mock_event_system):
    client = TestClient(app_with_mocks)

    response = client.get("/api/system/webhooks")

    assert response.status_code == 200
    data = response.json()
    assert "webhooks" in data
    assert len(data["webhooks"]) == 2
    assert "https://example.com/hook1" in data["webhooks"]
    mock_event_system.list_webhooks.assert_called_once()


def test_add_webhook(app_with_mocks, mock_event_system):
    client = TestClient(app_with_mocks)

    payload = {"url": "https://example.com/new-hook"}
    response = client.post("/api/system/webhooks", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Webhook added successfully"
    mock_event_system.add_webhook.assert_called_once_with(
        "https://example.com/new-hook"
    )


def test_add_webhook_invalid_url(app_with_mocks):
    client = TestClient(app_with_mocks)

    payload = {"url": "not-a-valid-url"}
    response = client.post("/api/system/webhooks", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert "Invalid URL" in data["detail"]


def test_add_webhook_failed(app_with_mocks, mock_event_system):
    mock_event_system.add_webhook.return_value = False
    client = TestClient(app_with_mocks)

    payload = {"url": "https://example.com/new-hook"}
    response = client.post("/api/system/webhooks", json=payload)

    assert response.status_code == 500
    data = response.json()
    assert "Failed to add webhook" in data["detail"]


def test_remove_webhook(app_with_mocks, mock_event_system):
    client = TestClient(app_with_mocks)

    response = client.delete(
        "/api/system/webhooks", params={"url": "https://example.com/hook1"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Webhook removed successfully"
    mock_event_system.remove_webhook.assert_called_once_with(
        "https://example.com/hook1"
    )


def test_remove_webhook_failed(app_with_mocks, mock_event_system):
    mock_event_system.remove_webhook.return_value = False
    client = TestClient(app_with_mocks)

    response = client.delete(
        "/api/system/webhooks", params={"url": "https://example.com/nonexistent"}
    )

    assert response.status_code == 404
    data = response.json()
    assert "Webhook not found" in data["detail"]


def test_get_stream_info(app_with_mocks, mock_streaming_stt):
    client = TestClient(app_with_mocks)

    response = client.get("/api/system/stream/test_stream/info")

    assert response.status_code == 200
    data = response.json()
    assert data["stream_id"] == "test_stream"
    assert "rms_history" in data
    assert "buffered_seconds" in data
    mock_streaming_stt.get_session_info.assert_called_once_with("test_stream")


def test_get_silero_decision(app_with_mocks, mock_streaming_stt):
    client = TestClient(app_with_mocks)

    response = client.get(
        "/api/system/stream/test_stream/silero", params={"tail_seconds": 5.0}
    )

    assert response.status_code == 200
    data = response.json()
    assert "decisions" in data
    assert len(data["decisions"]) == 2
    assert data["decisions"][0]["decision"] == "speech"
    mock_streaming_stt.get_silero_decision.assert_called_once_with("test_stream", 5.0)


def test_get_silero_decision_silero_not_available(app_with_mocks, mock_streaming_stt):
    mock_streaming_stt.SILERO_AVAILABLE = False
    client = TestClient(app_with_mocks)

    response = client.get("/api/system/stream/test_stream/silero")

    assert response.status_code == 503
    data = response.json()
    assert "Silero VAD not available" in data["detail"]


def test_get_stream_info_missing_stream(app_with_mocks, mock_streaming_stt):
    mock_streaming_stt.get_session_info.return_value = None
    client = TestClient(app_with_mocks)

    response = client.get("/api/system/stream/nonexistent/info")

    assert response.status_code == 404
    data = response.json()
    assert "Stream not found" in data["detail"]


def test_system_health_endpoint(app_with_mocks):
    client = TestClient(app_with_mocks)

    response = client.get("/api/system/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "unhealthy"]
    assert "timestamp" in data


def test_system_metrics(app_with_mocks):
    client = TestClient(app_with_mocks)

    with patch("psutil.cpu_percent", return_value=45.2), patch(
        "psutil.virtual_memory"
    ) as mock_memory:

        mock_memory.return_value.percent = 68.5
        mock_memory.return_value.used = 8589934592  # 8GB
        mock_memory.return_value.total = 17179869184  # 16GB

        response = client.get("/api/system/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data
        assert "memory_percent" in data
        assert data["cpu_percent"] == 45.2
        assert data["memory_percent"] == 68.5

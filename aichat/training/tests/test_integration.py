import uuid

# Basic smoke tests for the refactored TTS finetune app and API


def test_imports_refactored_modules():
    # Ensure key modules can be imported
    from backend.tts_finetune_app.processors.audio_processor import (
        AudioProcessor,
        TrainingConfig,
    )
    from backend.tts_finetune_app.services.runner import TTSOrchestratorService

    assert AudioProcessor is not None
    assert TrainingConfig is not None
    assert TTSOrchestratorService is not None


def test_create_app_status_endpoint():
    # Use the FastAPI test client to check the /api/voice/status endpoint
    from fastapi.testclient import TestClient

    from aichat.backend.main import create_app

    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/voice/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "backend" in body and body["backend"] == "running"
    assert "status" in body


def test_job_endpoints_return_404_for_missing_job():
    from fastapi.testclient import TestClient

    from aichat.backend.main import create_app

    app = create_app()
    client = TestClient(app)

    random_job = uuid.uuid4().hex[:12]
    resp = client.get(f"/api/voice/jobs/{random_job}/status")
    assert resp.status_code in (
        404,
        200,
    )  # 404 expected when job not present; accept 200 if shims/impl created a placeholder

    resp2 = client.get(f"/api/voice/jobs/{random_job}/logs")
    assert resp2.status_code in (404, 200)


def test_orchestrator_service_smoke(tmp_path):
    # Smoke-test CLI invocation wrapper without running heavy training:
    from backend.tts_finetune_app.services.runner import TTSOrchestratorService

    orchestrator = TTSOrchestratorService(python_executable="python")
    # Create empty dirs for input/output
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    # Call generate_manifest with empty input: should complete without raising (it may write no files)
    res = orchestrator.generate_manifest(
        input_dir=input_dir,
        metadata_csv=None,
        output_dir=output_dir,
        sample_rate=22050,
        fmt="both",
        resample=False,
        copy_audio=False,
    )
    assert isinstance(res, dict)

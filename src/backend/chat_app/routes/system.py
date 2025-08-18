from fastapi import APIRouter, Query, Body, HTTPException
import asyncio
import psutil
import time
from typing import Optional, Any, Dict, List

# Import the streaming STT service helpers
from backend.chat_app.services import streaming_stt_service as stt

# Event system for webhook management
from event_system import get_event_system

router = APIRouter()

# Store startup time
startup_time = time.time()


@router.get("/status")
async def get_system_status():
    """
    Get system status information including resource usage and uptime
    """
    try:
        # Get system metrics
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Calculate uptime
        uptime = time.time() - startup_time
        
        return {
            "status": "running",
            "uptime": uptime,
            "cpu_usage": cpu_usage,
            "memory_usage": memory.percent,
            "disk_usage": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            },
            "services": {
                "api": "running",
                "websocket": "running",
                "event_system": "running"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {e}")


@router.get("/vad_diagnostics")
async def vad_diagnostics(stream_id: str = Query(...), tail_seconds: float = 6.0):
    """
    Return VAD diagnostics for a given stream_id.

    Response:
    {
      "session": { ... session info including rms_history, buffered_seconds, last_voice_time ... } | null,
      "silero": list | null | {"error": "..."}
    }

    - session: returned by streaming_stt_service.get_session_info
    - silero: speech timestamps detected by Silero VAD on the tail window, or null if Silero unavailable
    """
    # Get session info synchronously
    session_info = stt.get_session_info(stream_id)

    # Run silero decision in executor (synchronous helper) to avoid blocking loop
    silero_result: Optional[Any] = None
    loop = asyncio.get_event_loop()

    try:
        if stt.SILERO_AVAILABLE:
            silero_result = await loop.run_in_executor(None, stt.get_silero_decision, stream_id, float(tail_seconds))
        else:
            silero_result = None
    except Exception as e:
        silero_result = {"error": str(e)}

    return {
        "session": session_info,
        "silero": silero_result
    }


# ---------------------------
# Webhook management endpoints
# ---------------------------

@router.get("/webhooks")
async def list_webhooks():
    """
    List registered external webhook URLs.
    Returns: { "webhooks": [ "https://example.com/hook", ... ] }
    """
    try:
        event_system = get_event_system()
        webhooks: List[str] = await event_system.list_webhooks()
        return {"webhooks": webhooks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list webhooks: {e}")


@router.post("/webhooks")
async def register_webhook(payload: Dict[str, str] = Body(...)):
    """
    Register a webhook URL to receive event POSTs.
    Body: { "url": "https://your.receiver/endpoint" }
    """
    try:
        url = payload.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="Missing 'url' in request body")

        event_system = get_event_system()
        await event_system.add_webhook(url)
        return {"status": "ok", "message": f"Webhook registered: {url}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register webhook: {e}")


@router.delete("/webhooks")
async def remove_webhook(url: str = Query(...)):
    """
    Remove a registered webhook by URL.
    Query: ?url=https://your.receiver/endpoint
    """
    try:
        event_system = get_event_system()
        await event_system.remove_webhook(url)
        return {"status": "ok", "message": f"Webhook removed: {url}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove webhook: {e}")


@router.post("/webhooks/test")
async def trigger_test_event(message: str = Body("test event")):
    """
    Trigger a test event that will be emitted through the EventSystem and forwarded to webhooks.
    Body (optional): raw message string.
    """
    try:
        event_system = get_event_system()
        await event_system.emit(
            # use a generic INFO-level system status event for test deliveries
            stt.EventType.SERVICE_STARTED if False else getattr(__import__("event_system"), "EventType").SERVICE_STARTED,
            f"Webhook test: {message}",
            {"test_message": message}
        )
        return {"status": "ok", "message": "Test event emitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to emit test event: {e}")
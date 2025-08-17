from fastapi import APIRouter, Query
import asyncio
from typing import Optional, Any, Dict

# Import the streaming STT service helpers
from backend.chat_app.services import streaming_stt_service as stt

router = APIRouter()


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
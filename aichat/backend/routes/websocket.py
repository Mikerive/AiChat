"""
WebSocket endpoints for real-time communication
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List

# Third-party imports
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

# Local imports
from aichat.backend.services.chat.service_manager import (
from aichat.constants.paths import TEMP_AUDIO_DIR, ensure_dirs
from aichat.core.event_system import EventType, get_event_system
                    from aichat.backend.services.voice.tts.piper_tts_service import (
                    from aichat.backend.services.voice.tts.piper_tts_service import (
                from aichat.backend.services.stt_services.streaming_stt_service import (
            from backend.api.routes.system import get_system_status

        # Decode base64 audio data
        audio_bytes = base64.b64decode(audio_data)

        # Save to centralized temporary file for processing
        ensure_dirs(TEMP_AUDIO_DIR)
        temp_path = str(
            TEMP_AUDIO_DIR / f"chunk_{stream_id}_{int(time.time()*1000)}.wav"
        )
        with open(temp_path, "wb") as temp_file:
            temp_file.write(audio_bytes)

        try:
            # Speech-to-Text Pipeline: Whisper STT Service
            whisper_service = get_whisper_service()
            transcription_result = await whisper_service.transcribe_audio(temp_path)

            # Emit transcription complete event
            event_system = get_event_system()
            await event_system.emit(
                EventType.AUDIO_TRANSCRIBED,
                "Speech-to-text transcription completed",
                {
                    "stream_id": stream_id,
                    "text": transcription_result.get("text", ""),
                    "language": transcription_result.get("language", ""),
                    "confidence": transcription_result.get("confidence", 0.0),
                },
            )

            # Send transcription result to frontend
            transcription_response = {
                "type": "transcription",
                "event": "transcription_complete",
                "stream_id": stream_id,
                "text": transcription_result.get("text", ""),
                "language": transcription_result.get("language", ""),
                "confidence": transcription_result.get("confidence", 0.0),
                "timestamp": "2024-01-01T00:00:00Z",
            }
            await websocket.send_text(json.dumps(transcription_response))
            try:
                await asyncio.sleep(0.01)
            except Exception:
                pass

            # Text sent to Chat Service for LLM Processing
            if transcription_result.get("text"):
                chat_service = get_chat_service()
                current_character = await chat_service.get_current_character()

                if current_character:
                    # LLM Processing: OpenRouter Service
                    chat_response = await chat_service.process_message(
                        transcription_result["text"],
                        current_character["id"],
                        current_character["name"],
                    )

                    # Emit response generated event
                    await event_system.emit(
                        EventType.CHAT_RESPONSE,
                        "LLM response generated",
                        {
                            "stream_id": stream_id,
                            "user_input": transcription_result["text"],
                            "character_response": chat_response.response,
                            "emotion": chat_response.emotion,
                            "model_used": chat_response.model_used,
                        },
                    )

                    # Text-to-Speech Pipeline: Piper TTS Service
                    tts_audio_path = await chat_service.generate_tts(
                        chat_response.response,
                        current_character["id"],
                        current_character["name"],
                    )

                    # Audio Generation Event
                    await event_system.emit(
                        EventType.AUDIO_GENERATED,
                        "TTS audio generation completed",
                        {
                            "stream_id": stream_id,
                            "audio_file": (
                                str(tts_audio_path) if tts_audio_path else None
                            ),
                            "text": chat_response.response,
                            "character": current_character["name"],
                        },
                    )

                    # Send complete response to frontend
                    complete_response = {
                        "type": "chat_complete",
                        "event": "response_ready",
                        "stream_id": stream_id,
                        "user_input": transcription_result["text"],
                        "character_response": chat_response.response,
                        "emotion": chat_response.emotion,
                        "audio_file": str(tts_audio_path) if tts_audio_path else None,
                        "timestamp": "2024-01-01T00:00:00Z",
                    }
                    await websocket.send_text(json.dumps(complete_response))

        finally:
            # Clean up temporary file
            os.unlink(temp_path)

    except Exception as e:
        logger.error(f"Error processing audio stream chunk: {e}")
        error_response = {
            "type": "error",
            "event": "audio_processing_error",
            "stream_id": stream_id,
            "message": str(e),
            "timestamp": "2024-01-01T00:00:00Z",
        }
        await websocket.send_text(json.dumps(error_response))

# Subscribe to all events when the module is loaded (async-safe)
event_system = get_event_system()

try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(event_system.subscribe_to_all(handle_event_broadcast))
    else:
        loop.run_until_complete(event_system.subscribe_to_all(handle_event_broadcast))
except Exception:
    # If event system fails, continue without it
    pass

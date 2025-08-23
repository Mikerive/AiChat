"""
Voice training API endpoints for VTuber backend
"""

import logging
from typing import Optional
from pathlib import Path

# Third-party imports
from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

# Local imports
import json
from aichat.backend.services.audio.audio_io_service import AudioIOService
from aichat.backend.services.di_container import (
    get_whisper_service,
    get_audio_io_service,
)
from aichat.models.schemas import (
    AudioDeviceInfo,
    AudioDevicesResponse,
    AudioDeviceSetResponse,
    AudioRecordResponse,
    AudioPlayResponse,
    AudioVolumeResponse,
    AudioInfoResponse,
    AudioIOStatusResponse,
    RecordTranscribeResponse,
    JobCheckpointResponse,
    JobLogsResponse,
)
from aichat.training.processors.audio_processor import AudioProcessor
from aichat.training.train_voice import VoiceTrainer, VoiceTrainerConfig
from aichat.constants.paths import (
    LOGS_DIR,
    MODELS_DIR,
    TTS_TRAINING_CHECKPOINTS,
    ensure_dirs
)
from aichat.core.database import db_ops
from aichat.core.event_system import (
    get_event_system,
    EventType,
    EventSeverity
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency injection using DI container
def get_audio_io_service_dep():
    """Dependency for AudioIO service using DI container"""
    return get_audio_io_service()

def get_whisper_service_dep():
    """Dependency injection for whisper service using DI container"""
    return get_whisper_service()

@router.get("/jobs/{job_id}/checkpoint", response_model=JobCheckpointResponse)
async def job_checkpoint(job_id: str):
    """Get checkpoint data for a training job"""
    try:
        job_path = TTS_TRAINING_CHECKPOINTS / f"{job_id}.json"
        if not job_path.exists():
            raise HTTPException(status_code=404, detail="Job checkpoint not found")
        data = json.loads(job_path.read_text(encoding="utf-8"))
        return JobCheckpointResponse(job_id=job_id, checkpoint=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading job checkpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}/logs", response_model=JobLogsResponse)
async def job_logs(job_id: str, tail: int = 200):
    """Return the last N lines of the orchestrator or events logs for a given job"""
    try:
        logs_dir = LOGS_DIR
        ensure_dirs(logs_dir)
        # Prioritize model-specific training.log
        model_log = MODELS_DIR / job_id / "training.log"
        event_log = logs_dir / "events.log"
        target = (
            model_log
            if model_log.exists()
            else event_log if event_log.exists() else None
        )
        if not target:
            raise HTTPException(status_code=404, detail="No logs found for job")
        # Read last N lines
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        tail_lines = lines[-tail:]
        return JobLogsResponse(job_id=job_id, log_file=str(target), tail="".join(tail_lines))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading job logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== AudioIO Service Endpoints =====

@router.get("/audio/devices", response_model=AudioDevicesResponse)
async def get_audio_devices(audio_io_service=Depends(get_audio_io_service_dep)):
    """Get available audio input and output devices"""
    try:
        input_devices = await audio_io_service.get_input_devices()
        output_devices = await audio_io_service.get_output_devices()

        return AudioDevicesResponse(
            input_devices=[
                AudioDeviceInfo(
                    id=device.id,
                    name=device.name,
                    channels=device.channels,
                    sample_rate=device.sample_rate,
                    is_default=device.is_default,
                )
                for device in input_devices
            ],
            output_devices=[
                AudioDeviceInfo(
                    id=device.id,
                    name=device.name,
                    channels=device.channels,
                    sample_rate=device.sample_rate,
                    is_default=device.is_default,
                )
                for device in output_devices
            ],
        )

    except Exception as e:
        logger.error(f"Error getting audio devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audio/input-device/{device_id}")
async def set_input_device(
    device_id: int, audio_io_service=Depends(get_audio_io_service_dep)
):
    """Set the current audio input device"""
    try:
        success = await audio_io_service.set_input_device(device_id)

        if success:
            return {"status": "success", "device_id": device_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to set input device")

    except Exception as e:
        logger.error(f"Error setting input device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audio/output-device/{device_id}")
async def set_output_device(
    device_id: int, audio_io_service=Depends(get_audio_io_service_dep)
):
    """Set the current audio output device"""
    try:
        success = await audio_io_service.set_output_device(device_id)

        if success:
            return {"status": "success", "device_id": device_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to set output device")

    except Exception as e:
        logger.error(f"Error setting output device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audio/record")
async def record_audio(
    duration: float = 5.0, audio_io_service=Depends(get_audio_io_service_dep)
):
    """Record audio from the current input device"""
    try:
        if duration <= 0 or duration > 300:  # Max 5 minutes
            raise HTTPException(
                status_code=400, detail="Duration must be between 0 and 300 seconds"
            )

        audio_path = await audio_io_service.record_audio(duration)

        if audio_path and audio_path.exists():
            # Get audio info
            audio_info = await audio_io_service.get_audio_info(audio_path)

            return {
                "status": "success",
                "audio_path": str(audio_path),
                "duration": duration,
                "file_size": audio_path.stat().st_size,
                "audio_info": audio_info,
            }
        else:
            raise HTTPException(status_code=500, detail="Recording failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audio/play")
async def play_audio(
    audio_path: str, audio_io_service=Depends(get_audio_io_service_dep)
):
    """Play audio file through the current output device"""
    try:
        audio_file = Path(audio_path)

        if not audio_file.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

        success = await audio_io_service.play_audio(audio_file)

        if success:
            return {"status": "success", "audio_path": audio_path}
        else:
            raise HTTPException(status_code=500, detail="Playback failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error playing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audio/volume")
async def set_volume(request: dict = Body(...), audio_io_service=Depends(get_audio_io_service_dep)):
    """Set output volume (0.0 to 1.0)"""
    try:
        volume = request.get("volume")
        if volume is None:
            raise HTTPException(status_code=400, detail="Volume field required in request body")
        
        if not isinstance(volume, (int, float)):
            raise HTTPException(status_code=400, detail="Volume must be a number")
            
        if volume < 0.0 or volume > 1.0:
            raise HTTPException(
                status_code=400, detail="Volume must be between 0.0 and 1.0"
            )

        success = await audio_io_service.set_volume(float(volume))

        if success:
            return {"status": "success", "volume": volume}
        else:
            raise HTTPException(status_code=500, detail="Failed to set volume")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting volume: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audio/info")
async def get_audio_file_info(
    audio_path: str, audio_io_service=Depends(get_audio_io_service_dep)
):
    """Get information about an audio file"""
    try:
        audio_file = Path(audio_path)

        if not audio_file.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

        audio_info = await audio_io_service.get_audio_info(audio_file)

        if audio_info:
            return {"status": "success", "audio_info": audio_info}
        else:
            raise HTTPException(status_code=500, detail="Failed to get audio info")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audio/status")
async def get_audio_io_status(audio_io_service=Depends(get_audio_io_service_dep)):
    """Get AudioIO service status"""
    try:
        status = await audio_io_service.get_service_status()
        return {"status": "success", "audio_io": status}

    except Exception as e:
        logger.error(f"Error getting audio IO status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class RecordMicrophoneRequest(BaseModel):
    """Request model for microphone recording and transcription"""

    duration: float = 5.0

@router.post("/audio/record-and-transcribe")
async def record_and_transcribe(
    req: RecordMicrophoneRequest, whisper_service=Depends(get_whisper_service_dep)
):
    """Record audio from microphone and transcribe it"""
    try:
        if req.duration <= 0 or req.duration > 300:  # Max 5 minutes
            raise HTTPException(
                status_code=400, detail="Duration must be between 0 and 300 seconds"
            )

        # Use WhisperService's enhanced microphone transcription
        result = await whisper_service.transcribe_microphone(req.duration)

        return {"status": "success", "transcription": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in record and transcribe: {e}")
        raise HTTPException(status_code=500, detail=str(e))

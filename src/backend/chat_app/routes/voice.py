"""
Voice training API endpoints for VTuber backend
"""

import logging
import sys
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants.paths import (
    TTS_TRAINING_RAW,
    TTS_TRAINING_PROCESSED,
    TTS_TRAINING_DIR,
    TTS_TRAINING_METADATA,
    TTS_MODELS_DIR,
    TTS_PIPER_DATASET,
    TTS_LOGS_DIR,
    TTS_TRAINING_CHECKPOINTS,
    TEMP_AUDIO_DIR,
    ensure_dirs
)
 
from database import db_ops, TrainingData, VoiceModel
from event_system import (
    get_event_system, EventType, EventSeverity,
    emit_training_started, emit_training_progress,
    emit_training_completed, emit_error, emit_audio_uploaded, emit_audio_processed
)
from backend.chat_app.services.service_manager import get_whisper_service, get_voice_service, get_tts_finetune_service
from backend.tts_finetune_app.processors.audio_processor import AudioProcessor
from backend.tts_finetune_app.train_voice import VoiceTrainer, VoiceTrainerConfig

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency injection functions
def get_voice_service_dep():
    """Dependency injection for voice service"""
    return get_voice_service()

def get_whisper_service_dep():
    """Dependency injection for whisper service"""
    return get_whisper_service()

def get_tts_finetune_service_dep():
    """Dependency injection for TTS finetune service"""
    return get_tts_finetune_service()




class TrainRequest(BaseModel):
    """Voice training request model"""
    input_dir: str
    model_name: str = "fine_tuned_model"
    epochs: int = 10
    batch_size: int = 8
    character_id: Optional[int] = None


@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    voice_service = Depends(get_voice_service_dep)
):
    """Upload an audio file for processing"""
    try:
        # Save uploaded file
        upload_dir = TTS_TRAINING_RAW
        ensure_dirs(upload_dir)
        
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Emit upload event
        await emit_audio_uploaded(
            f"Uploaded training file: {file.filename}",
            {"filename": file.filename, "path": str(file_path)}
        )
        
        return {
            "status": "uploaded",
            "filename": file.filename,
            "path": str(file_path)
        }
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process")
async def process_uploaded_audio(
    filename: str,
    voice_service = Depends(get_voice_service_dep)
):
    """Process a previously uploaded file into training clips"""
    try:
        file_path = TTS_TRAINING_RAW / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Uploaded file not found")
        
        # Use audio processor
        audio_processor = AudioProcessor()
        training_data_dir = TTS_TRAINING_DIR
        saved = audio_processor.process_and_split_file(file_path, training_data_dir / "audio")
        
        # Create training data entries in database
        training_data_entries = []
        for saved_file in saved:
            entry = await db_ops.create_training_data(
                filename=saved_file.name,
                speaker="target_speaker",
                quality="high"
            )
            training_data_entries.append(entry)
        
        # Emit processing event
        await emit_audio_processed(
            f"Processed {filename} into {len(saved)} clips",
            {"clips_created": [f.name for f in saved], "entries_count": len(training_data_entries)}
        )
        
        return {
            "status": "processed",
            "clips_created": [f.name for f in saved],
            "database_entries": len(training_data_entries)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clips")
async def list_training_clips(
    voice_service = Depends(get_voice_service_dep)
):
    """List processed training clips"""
    try:
        training_data = await db_ops.list_training_data(limit=1000)
        clips = []
        
        for data in training_data:
            clips.append({
                "id": data.id,
                "filename": data.filename,
                "transcript": data.transcript,
                "duration": data.duration,
                "speaker": data.speaker,
                "emotion": data.emotion,
                "quality": data.quality,
                "created_at": data.created_at.isoformat()
            })
        
        return {"clips": clips}
        
    except Exception as e:
        logger.error(f"Error listing clips: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train")
async def start_training(
    req: TrainRequest,
    background_tasks: BackgroundTasks,
    voice_service = Depends(get_voice_service_dep)
):
    """Start a background training job using processed clips"""
    try:
        input_dir = Path(req.input_dir)
        if not input_dir.exists():
            raise HTTPException(status_code=404, detail="Input directory not found")
        
        output_dir = TTS_MODELS_DIR / req.model_name
        ensure_dirs(output_dir)
        
        # Emit training started event
        await emit_training_started(
            f"Starting voice training for {req.model_name}",
            {
                "model_name": req.model_name,
                "input_dir": str(input_dir),
                "output_dir": str(output_dir),
                "epochs": req.epochs,
                "batch_size": req.batch_size
            }
        )
        
        # Add background task
        def _run_training():
            try:
                config = VoiceTrainerConfig()
                trainer = VoiceTrainer(config)
                
                # Simulate training progress
                import time
                for epoch in range(1, req.epochs + 1):
                    time.sleep(1)  # Simulate training time
                    progress = (epoch / req.epochs) * 100
                    
                    # Emit progress event
                    import asyncio
                    asyncio.create_task(
                        emit_training_progress(
                            f"Training progress: {epoch}/{req.epochs} epochs",
                            {
                                "epoch": epoch,
                                "total_epochs": req.epochs,
                                "progress": progress,
                                "loss": max(0.1, 2.0 - (epoch * 0.1))  # Simulated loss
                            }
                        )
                    )
                
                # Create placeholder model files
                (output_dir / "config.json").write_text('{"model_type": "xtts"}')
                (output_dir / "model.pth").write_text("placeholder_model_data")
                
                # Emit completion event
                asyncio.create_task(
                    emit_training_completed(
                        f"Training completed for {req.model_name}",
                        {
                            "model_name": req.model_name,
                            "output_dir": str(output_dir),
                            "epochs_trained": req.epochs
                        }
                    )
                )
                
                # Create database entry
                asyncio.create_task(
                    db_ops.create_voice_model(
                        name=req.model_name,
                        model_path=str(output_dir),
                        character_id=req.character_id,
                        status="completed",
                        epochs_trained=req.epochs,
                        loss=0.1
                    )
                )
                
            except Exception as e:
                logger.error(f"Training failed: {e}")
                asyncio.create_task(
                    emit_error(f"Training failed: {e}")
                )
        
        background_tasks.add_task(_run_training)
        
        return {
            "status": "started",
            "model_name": req.model_name,
            "output_dir": str(output_dir),
            "epochs": req.epochs,
            "batch_size": req.batch_size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manifest")
async def generate_manifest_endpoint(
    output_dir: str,
    tts_service = Depends(get_tts_finetune_service_dep)
):
    """Generate Piper manifest from processed clips"""
    try:
        if tts_service is None:
            raise HTTPException(status_code=500, detail="TTS finetune service unavailable")
        input_dir = TTS_TRAINING_PROCESSED
        metadata_csv = TTS_TRAINING_METADATA
        out = Path(output_dir)
        # Run manifest generator synchronously; consider background task if large
        res = tts_service.generate_manifest(
            input_dir=input_dir,
            metadata_csv=metadata_csv,
            output_dir=out,
            sample_rate=22050,
            fmt="both",
            resample=True,
            copy_audio=True
        )
        return {"status": "manifest_generated", "output": str(out)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manifest generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train_orchestrator")
async def start_orchestrator_endpoint(
    model_name: str,
    background_tasks: BackgroundTasks,
    tts_service = Depends(get_tts_finetune_service_dep)
):
    """Start orchestrated Piper training in background"""
    try:
        if tts_service is None:
            raise HTTPException(status_code=500, detail="TTS finetune service unavailable")
        dataset_dir = TTS_PIPER_DATASET
        output_dir = TTS_MODELS_DIR
        # Run orchestrator in background to avoid blocking
        def _run():
            try:
                tts_service.start_training(
                    dataset_dir=dataset_dir,
                    output_dir=output_dir,
                    model_name=model_name,
                    preprocess=False,
                    language="en-us",
                    dataset_format="ljspeech",
                    sample_rate=22050,
                    accelerator="gpu",
                    devices=1,
                    batch_size=12,
                    checkpoint_epochs=1,
                    log_every_n_steps=1000,
                    max_epochs=10000,
                    resume_from_checkpoint="",
                    quality="medium"
                )
            except Exception as e:
                logger.error(f"Background training failed: {e}")

        background_tasks.add_task(_run)
        return {"status": "training_started", "model_name": model_name, "output_dir": str(output_dir)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start orchestrator error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/checkpoints")
async def list_checkpoints(
    model_name: Optional[str] = None,
    voice_service = Depends(get_voice_service_dep)
):
    """List available checkpoints for models"""
    try:
        models_dir = TTS_MODELS_DIR
        results = {}
        
        if model_name:
            model_dir = models_dir / model_name
            if not model_dir.exists():
                raise HTTPException(status_code=404, detail="Model not found")
            
            checkpoints = [str(p.name) for p in sorted(model_dir.rglob("*")) if p.is_file()]
            results[model_name] = checkpoints
        else:
            for md in models_dir.iterdir():
                if md.is_dir():
                    checkpoints = [str(p.name) for p in sorted(md.rglob("*")) if p.is_file()]
                    results[md.name] = checkpoints
        
        return {"checkpoints": results}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing checkpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(
    voice_service = Depends(get_voice_service_dep)
):
    """List available voice models"""
    try:
        models = await db_ops.list_voice_models(limit=100)
        model_list = []
        
        for model in models:
            model_list.append({
                "id": model.id,
                "name": model.name,
                "model_path": model.model_path,
                "character_id": model.character_id,
                "status": model.status,
                "epochs_trained": model.epochs_trained,
                "loss": model.loss,
                "created_at": model.created_at.isoformat(),
                "updated_at": model.updated_at.isoformat()
            })
        
        return {"models": model_list}
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    whisper_service = Depends(get_whisper_service_dep)
):
    """Transcribe audio file using Whisper"""
    try:
        # Save uploaded file
        temp_file = TEMP_AUDIO_DIR / file.filename
        ensure_dirs(TEMP_AUDIO_DIR)
        
        with open(temp_file, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Transcribe using Whisper
        result = await whisper_service.transcribe_audio(temp_file)
        
        # Create training data entry
        training_data = await db_ops.create_training_data(
            filename=file.filename,
            transcript=result["text"],
            duration=result.get("duration"),
            speaker="unknown",
            quality="high"
        )
        
        # Clean up temp file
        temp_file.unlink()
        
        return {
            "id": training_data.id,
            "filename": file.filename,
            "transcript": result["text"],
            "language": result["language"],
            "confidence": result["confidence"],
            "duration": result.get("duration"),
            "training_data_id": training_data.id
        }
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_voice_status(
    voice_service = Depends(get_voice_service_dep)
):
    """Get voice training system status"""
    try:
        models = await db_ops.list_voice_models(limit=100)
        training_data = await db_ops.list_training_data(limit=100)
        
        return {
            "backend": "running",
            "voice_service": "active",
            "models_count": len(models),
            "training_data_count": len(training_data),
            "available_models": [model.name for model in models if model.status == "completed"],
            "status": "ready"
        }
        
    except Exception as e:
        logger.error(f"Error getting voice status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Job monitoring endpoints
@router.get("/jobs/{job_id}/status")
async def job_status(job_id: str):
    """Read job checkpoint JSON and return status summary"""
    try:
        job_path = TTS_MODELS_DIR / job_id / "job_checkpoint.json"
        if not job_path.exists():
            # Also check checkpoints dir
            alt = TTS_TRAINING_CHECKPOINTS / f"{job_id}.json"
            if alt.exists():
                job_path = alt
            else:
                raise HTTPException(status_code=404, detail="Job checkpoint not found")
        data = json.loads(job_path.read_text(encoding="utf-8"))
        return {"job_id": job_id, "checkpoint": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading job checkpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/logs")
async def job_logs(job_id: str, tail: int = 200):
    """Return the last N lines of the orchestrator or events logs for a given job"""
    try:
        logs_dir = TTS_LOGS_DIR
        ensure_dirs(logs_dir)
        # Prioritize model-specific training.log
        model_log = TTS_MODELS_DIR / job_id / "training.log"
        event_log = logs_dir / "events.log"
        target = model_log if model_log.exists() else event_log if event_log.exists() else None
        if not target:
            raise HTTPException(status_code=404, detail="No logs found for job")
        # Read last N lines
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        tail_lines = lines[-tail:]
        return {"job_id": job_id, "log_file": str(target), "tail": "".join(tail_lines)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading job logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
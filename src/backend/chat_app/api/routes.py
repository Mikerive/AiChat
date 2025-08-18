"""
REST API routes for VTuber backend (recreated)
This file includes core chat endpoints and added voice_trainer endpoints
for uploading/processing audio, listing clips, starting training, and listing checkpoints.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

logger = logging.getLogger(__name__)

# Minimal placeholders for pipeline/character loader so API can start.
# In the original project these are provided by other modules. If you restore those modules,
# replace these placeholders with the real imports.
try:
    from ..config import config  # type: ignore
except Exception:
    config = None

# Placeholder character loader
class _DummyCharacter:
    def __init__(self):
        self.background = type("B", (), {"name": "Hatsune Miku"})
        self.personality = type("P", (), {"core_traits": [], "speaking_style": "default"})
        self.metadata = {}

class CharacterLoader:
    def list_available_characters(self):
        return ["hatsune_miku", "default_assistant"]
    def get_character(self, name):
        return _DummyCharacter()

character_loader = CharacterLoader()
pipeline_instance = None  # In real app this will be VTuberPipeline instance

app = FastAPI(
    title="VTuber Backend API (recreated)",
    description="REST API for VTuber streaming backend (recreated routes)",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class TextMessage(BaseModel):
    text: str
    character: str = "hatsune_miku"

class CharacterSwitch(BaseModel):
    character: str

class TTSRequest(BaseModel):
    text: str
    character: str = "hatsune_miku"

@app.on_event("startup")
async def startup_event():
    """Placeholder startup initialization"""
    global pipeline_instance
    # In the original application pipeline_instance would be initialized here.
    logger.info("API startup - pipeline instance not initialized in this lightweight rebuild")

@app.get("/")
async def root():
    return {"message": "VTuber Backend API (recreated)", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "pipeline": "ready" if pipeline_instance else "not_ready",
        "character": getattr(pipeline_instance, "current_character", None) and getattr(pipeline_instance.current_character.background, "name", "none")
    }

@app.get("/characters")
async def list_characters():
    try:
        characters = character_loader.list_available_characters()
        character_details = []
        for char_name in characters:
            char = character_loader.get_character(char_name)
            if char:
                character_details.append({
                    "id": char_name,
                    "name": getattr(char.background, "name", char_name),
                    "description": getattr(char.metadata, "description", ""),
                    "traits": getattr(char.personality, "core_traits", []),
                    "speaking_style": getattr(char.personality, "speaking_style", "")
                })
        return {"characters": character_details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/characters/{character_id}")
async def get_character(character_id: str):
    try:
        character = character_loader.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        return {
            "id": character_id,
            "name": getattr(character.background, "name", "Unknown"),
            "description": getattr(character.metadata, "description", ""),
            "background": getattr(character.background, "__dict__", {}),
            "personality": getattr(character.personality, "__dict__", {}),
            "metadata": getattr(character, "metadata", {})
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_with_character(message: TextMessage):
    try:
        if not pipeline_instance:
            # Minimal echo behavior until pipeline is restored
            return {"user_input": message.text, "character": message.character, "character_name": message.character, "response": f"(echo) {message.text}"}
        # Otherwise real pipeline handling would occur
        raise HTTPException(status_code=501, detail="Full pipeline not available in this rebuild")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    try:
        if not pipeline_instance:
            return {"text": request.text, "character": request.character, "character_name": request.character, "audio_format": "wav", "status": "generated (placeholder)"}
        raise HTTPException(status_code=501, detail="Full TTS not available in this rebuild")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/switch_character")
async def switch_character(request: CharacterSwitch):
    try:
        if not pipeline_instance:
            # Simulate switch
            return {"character": request.character, "character_name": request.character, "greeting": f"Switched to {request.character}", "status": "switched"}
        raise HTTPException(status_code=501, detail="Full pipeline not available in this rebuild")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Character switch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status():
    try:
        return {
            "backend": "running",
            "pipeline": "ready" if pipeline_instance else "not_ready",
            "current_character": {
                "id": None,
                "name": getattr(pipeline_instance, "current_character", None) and getattr(pipeline_instance.current_character.background, "name", None)
            },
            "models": {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------
# Voice Trainer Endpoints
# -----------------------
VOICE_TRAINER_DIR = Path("backend/tts_finetune_app")
TRAINING_DATA_DIR = VOICE_TRAINER_DIR / "training_data"
TRAINING_AUDIO_DIR = TRAINING_DATA_DIR / "audio"
MODELS_OUTPUT_DIR = VOICE_TRAINER_DIR / "models"
RAW_UPLOAD_DIR = TRAINING_DATA_DIR / "raw"

# Ensure directories exist
for p in (TRAINING_DATA_DIR, TRAINING_AUDIO_DIR, MODELS_OUTPUT_DIR, RAW_UPLOAD_DIR):
    p.mkdir(parents=True, exist_ok=True)

@app.post("/voice_trainer/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Upload an mp4/mp3 file for processing"""
    try:
        filename = Path(file.filename).name
        dest = RAW_UPLOAD_DIR / filename
        with open(dest, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(f"Uploaded training file: {dest}")
        return {"status": "uploaded", "filename": filename, "path": str(dest)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice_trainer/process")
async def process_uploaded_audio(filename: str):
    """Process a previously uploaded file into training clips"""
    try:
        file_path = RAW_UPLOAD_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Uploaded file not found")
        # Use audio_processor if available
        try:
            from ..tts_finetune_app.processors.audio_processor import AudioProcessor  # type: ignore
            processor = AudioProcessor()
            saved = processor.process_and_split_file(file_path, TRAINING_AUDIO_DIR)
            names = [p.name for p in saved]
        except Exception as e:
            logger.warning(f"Processor unavailable or failed: {e}")
            names = []
        return {"status": "processed", "clips_created": names}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/voice_trainer/clips")
async def list_training_clips():
    """List processed training clips"""
    try:
        clips = []
        for p in sorted(TRAINING_AUDIO_DIR.glob("*.wav")):
            clips.append({
                "filename": p.name,
                "path": str(p),
                "size": p.stat().st_size,
                "modified": p.stat().st_mtime
            })
        return {"clips": clips}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TrainRequest(BaseModel):
    input_dir: str
    model_name: str = "fine_tuned_model"
    epochs: int = 10
    batch_size: int = 8

def _run_finetune_blocking(input_dir: str, output_dir: str, epochs: int, batch_size: int):
    """Blocking helper to call training CLI/class from a background thread"""
    try:
        # Attempt to import trainer and run fine_tune
        from ..tts_finetune_app.train_voice import VoiceTrainer, VoiceTrainerConfig  # type: ignore
        cfg = VoiceTrainerConfig()
        trainer = VoiceTrainer(cfg)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        trainer.fine_tune_voice(Path(input_dir), out_path, epochs=epochs, batch_size=batch_size)
    except Exception as e:
        logger.error(f"Background training failed: {e}")

@app.post("/voice_trainer/train")
async def start_training(req: TrainRequest, background_tasks: BackgroundTasks):
    """Start a background training job using processed clips"""
    try:
        input_dir = Path(req.input_dir)
        if not input_dir.exists():
            raise HTTPException(status_code=404, detail="Input directory not found")
        model_name = req.model_name
        output_dir = MODELS_OUTPUT_DIR / model_name
        background_tasks.add_task(_run_finetune_blocking, str(input_dir), str(output_dir), req.epochs, req.batch_size)
        return {"status": "started", "model_name": model_name, "output_dir": str(output_dir)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/voice_trainer/checkpoints")
async def list_checkpoints(model_name: Optional[str] = None):
    """List available checkpoints for models (all models if not specified)"""
    try:
        results = {}
        if model_name:
            model_dir = MODELS_OUTPUT_DIR / model_name
            if not model_dir.exists():
                raise HTTPException(status_code=404, detail="Model not found")
            ckpts = [str(p.name) for p in sorted(model_dir.glob("**/*")) if p.is_file()]
            results[model_name] = ckpts
        else:
            for md in MODELS_OUTPUT_DIR.iterdir():
                if md.is_dir():
                    ckpts = [str(p.name) for p in sorted(md.glob("**/*")) if p.is_file()]
                    results[md.name] = ckpts
        return {"checkpoints": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for streaming events in real-time
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        from event_system import get_event_system, EventType  # local import to avoid startup ordering issues
        event_system = get_event_system()
        # Register this websocket with the event system so subscribers get pushed events
        await event_system.add_websocket_connection(websocket)

        # Keep the connection open until the client disconnects.
        while True:
            # Wait for any incoming client message to keep the socket alive.
            # We don't expect messages from the client, but this will raise WebSocketDisconnect on disconnect.
            try:
                await websocket.receive_text()
            except Exception:
                # If receive fails, break and cleanup the connection.
                break

    except Exception as e:
        logger.debug(f"WebSocket connection error: {e}")
    finally:
        try:
            from event_system import get_event_system
            event_system = get_event_system()
            await event_system.remove_websocket_connection(websocket)
        except Exception:
            pass

# Aggregated logs endpoint - reads persistent event log and returns simple aggregates
@app.get("/logs/aggregate")
async def aggregate_logs(limit: int = 1000):
    """Return aggregated counts from the persistent events log and recent lines"""
    try:
        logs_path = Path("backend/tts_finetune_app/logs/events.log")
        if not logs_path.exists():
            return {"total": 0, "by_type": {}, "recent": []}

        import json as _json
        counts = {}
        recent = []
        with logs_path.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            # take the last `limit` lines for recent
            recent_lines = [l.strip() for l in lines[-limit:]]
            for l in recent_lines:
                if not l:
                    continue
                try:
                    ev = _json.loads(l)
                    et = ev.get("event_type")
                    counts[et] = counts.get(et, 0) + 1
                    recent.append(ev)
                except Exception:
                    continue

        return {"total": sum(counts.values()), "by_type": counts, "recent": recent}
    except Exception as e:
        logger.error(f"Error aggregating logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# Character Interactor & Voice Training Toolkit

A local-first toolkit for building, testing, and iterating on interactive character agents and training custom text-to-speech (TTS) voices.

This repository provides:
- A character interactor (persona-driven conversational agent) with conversation memory and profile management.
- A voice training pipeline for ingesting audio, producing Whisper transcripts, and generating Piper-compatible datasets for fine-tuning.
- Local STT/TTS integrations (Whisper for speech-to-text, Piper for text-to-speech).
- REST API and WebSocket event stream for realtime integrations.
- An optional Tkinter debugging GUI for local control and monitoring.

Quick links
- Configuration template: [`.env.example`](.env.example:1)
- Start backend: [`start_backend.py`](start_backend.py:1)
- Start GUI: [`start_gui.py`](start_gui.py:1)
- Voice training pipeline notes: [`src/backend/tts_finetune_app/README.md`](src/backend/tts_finetune_app/README.md:1)

Installation

Prerequisites
- Python 3.8+
- FFmpeg (for audio extraction)
- Optional: CUDA-compatible GPU for faster model training/transcription

Setup
1. Clone the repository
   git clone <repository-url>
   cd VtuberMiku

2. Create and activate a virtual environment (recommended)
   python -m venv venv
   venv\Scripts\activate    # Windows (cmd)
   source venv/bin/activate # macOS / Linux

3. Install dependencies
   python -m pip install --upgrade pip
   pip install -r requirements.txt

4. Configure environment
   cp .env.example .env
   # Edit `.env` to set API host/port, model paths, and API keys.

Usage

Start the backend (development)
python start_backend.py
# or
python main.py

Start the GUI (optional)
python start_gui.py

Accessing the API
- OpenAPI docs: http://localhost:8765/docs
- WebSocket: ws://localhost:8765/api/ws

API Overview

Chat
- GET /api/chat/characters
- POST /api/chat
- POST /api/chat/switch

TTS
- POST /api/tts

Voice training
- POST /api/voice/upload
- POST /api/voice/train
- GET /api/voice/models

System
- GET /health
- GET /api/system/status

WebSocket Events
Subscribe to realtime events (transcription, training progress, chat responses) via `/api/ws`. Clients may send a JSON subscribe message to filter event types.

Voice Training Pipeline

See detailed pipeline and implementation notes in [`src/backend/tts_finetune_app/README.md`](src/backend/tts_finetune_app/README.md:1). In brief:
- Ingest audio (mp3/mp4), extract WAV with FFmpeg
- Optional source-separation (Spleeter) to isolate vocals
- Silence-based clipping, resampling, normalization
- Whisper transcription to create transcripts and metadata
- Piper dataset manifest generation and fine-tuning with epoch-level checkpointing

Configuration

Important environment variables (set in `.env` or via your environment):
- API_HOST, API_PORT, DEBUG
- DATABASE_URL (default: sqlite:///./vtuber.db)
- WHISPER_MODEL, PIPER_MODEL_PATH, SAMPLE_RATE
- LOG_LEVEL, LOG_FILE
- OPENROUTER_API_KEY (optional; for LLM integration)

Development

- Run tests: pytest
- Format: black .
- Lint: flake8 .
- Type check: mypy .

Project structure (high level)
- backend/: FastAPI application and services
- src/backend/tts_finetune_app/: voice training pipeline and tools
- src/frontend/: optional Tkinter GUI
- tests/: unit and integration tests
- start_backend.py, start_gui.py: convenience scripts

Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new behavior
4. Open a pull request describing your changes

License

MIT License — see the LICENSE file

Acknowledgments

- FastAPI, Whisper, Piper, Tkinter

Note

This project was previously named and organized around VTuber use cases. It has been refocused to serve as a general-purpose Character Interactor and Voice Training Toolkit. Please update any tooling, documentation, or downstream references that still use the "VTuber" name.
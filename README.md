# Character Interactor & Voice Training Toolkit

Lightweight, local-first toolkit for building and iterating on persona-driven character agents and training custom text-to-speech (TTS) voices. The codebase combines a FastAPI backend (chat, TTS orchestration, voice fine-tuning hooks), an optional Tkinter debug GUI, and a voice finetune pipeline.

Overview
- Character interactor: persona management, chat endpoints, conversation memory.
- Voice training pipeline: ingest → segmentation → transcription → Piper manifest → fine-tune.
- REST API and WebSocket event stream for realtime integrations.
- Optional local GUI for monitoring and control.

Quickstart

Prerequisites
- Python 3.8+
- FFmpeg (for audio extraction)
- Optional: CUDA-capable GPU for faster Whisper / PyTorch operations

Install
1. Clone the repository
   git clone <repository-url>
   cd VtuberMiku

2. Create virtual environment
   python -m venv venv
   venv\Scripts\activate    # Windows (cmd)
   source venv/bin/activate # macOS / Linux

3. Install dependencies
   python -m pip install --upgrade pip
   pip install -r requirements.txt

4. Configure environment
   cp .env.example .env
   # Edit `.env` for API_HOST, API_PORT, model paths, and keys (see [`src/config.py`](src/config.py:1))

Running the project

Start backend (recommended; runs FastAPI)
python start_backend.py

Developer alternative (runs uvicorn from src)
cd src
python -m uvicorn backend.chat_app.main:create_app --factory --host localhost --port 8765 --reload

Start GUI (optional)
python start_gui.py

API & WebSocket
- OpenAPI docs: http://localhost:8765/docs
- WebSocket endpoint: ws://localhost:8765/api/ws

Repository layout (high level)

Top-level
- [`start_backend.py`](start_backend.py:1) — convenience script to start backend
- [`start_gui.py`](start_gui.py:1) — convenience script to start GUI
- [`main.py`](main.py:1) — main entrypoint used in some launch modes
- [`requirements.txt`](requirements.txt:1)
- [`README_STARTUP.md`](README_STARTUP.md:1) — startup notes and tips

Source (src/)
- [`src/backend/chat_app/`](src/backend/chat_app:1) — FastAPI application, routes, and services
  - routes: [`src/backend/chat_app/routes/`](src/backend/chat_app/routes:1)
  - services: [`src/backend/chat_app/services/`](src/backend/chat_app/services:1)
  - audio & model assets: [`src/backend/chat_app/audio/`](src/backend/chat_app/audio:1)
- [`src/backend/tts_finetune_app/`](src/backend/tts_finetune_app:1) — TTS finetune pipeline (processors, scripts, training_data)
  - Read the pipeline notes at [`src/backend/tts_finetune_app/README.md`](src/backend/tts_finetune_app/README.md:1)
- [`src/frontend/`](src/frontend:1) — optional Tkinter GUI and components (see [`src/frontend/gui.py`](src/frontend/gui.py:1))
- Configuration and utilities: [`src/config.py`](src/config.py:1), [`src/database.py`](src/database.py:1), [`src/event_system.py`](src/event_system.py:1)

Key implementation notes
- Voice training and manifests are expected under `backend/tts_finetune_app/` (paths referenced throughout routes and services).
  - training data: [`backend/tts_finetune_app/training_data/`](backend/tts_finetune_app/training_data:1)
  - model outputs: [`backend/tts_finetune_app/models/`](backend/tts_finetune_app/models:1)
- Piper runtime models are stored under [`backend/chat_app/audio/piper_models`](backend/chat_app/audio/piper_models:1) and generated audio is written to [`backend/chat_app/audio/generated`](backend/chat_app/audio/generated:1).
- Several route handlers reference the tts finetune locations — if you rename/move the TTS folder, update references in `src/backend/chat_app/routes/voice.py` and associated services.

Development
- Run tests: pytest
- Format: black .
- Lint: flake8 .
- Type check: mypy .

Contributing
1. Fork the repo
2. Create a feature branch
3. Add tests and update docs
4. Open a pull request

Notes for maintainers
- The repository contains historical/duplicate layout traces (e.g., `backend/voice_trainer` vs `backend/tts_finetune_app`). Search the codebase before large refactors.
- The GUI contains logic to start the backend by checking `src/backend/main.py` or `src/main.py` depending on your launch path — see [`src/frontend/gui.py`](src/frontend/gui.py:1).
- Implementation plan and architecture are in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md:1).

Useful references
- Implementation plan: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md:1)
- TTS pipeline notes: [`src/backend/tts_finetune_app/README.md`](src/backend/tts_finetune_app/README.md:1)
- Startup tips: [`README_STARTUP.md`](README_STARTUP.md:1)
- Tests: [`tests/`](tests:1)

License
MIT — see LICENSE

Acknowledgments
FastAPI, Whisper, Piper, Tkinter
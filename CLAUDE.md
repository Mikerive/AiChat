# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation
- **Install package**: `pip install -e .` (development mode)
- **Install with dependencies**: `pip install -e .[dev,gui,training]`

### Running the Application
- **Start backend**: `aichat-backend` or `aichat backend --host localhost --port 8765 --reload`
- **Start GUI**: `aichat-frontend` or `aichat frontend`
- **Start training**: `aichat-training` or `aichat training --mode serve`
- **CLI help**: `aichat --help`

### Testing and Quality
- **Run tests**: `pytest` or `pytest -q` for quiet output
- **Format code**: `black .`
- **Lint code**: `flake8 .`
- **Type check**: `mypy .` (may show warnings, use `|| true` to continue)

### Package Management
- **Install dependencies**: `pip install -r requirements.txt`
- **Development dependencies**: `pip install -r requirements-dev.txt`
- **Virtual environment**: `python -m venv venv` then `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)

## Project Architecture

### Repository Structure Map
```
aichat/                               # Main Python package
├── aichat/                           # Package source code
│   ├── constants/                    # Centralized constants and paths
│   ├── core/                         # Core infrastructure (config, database, events)
│   ├── models/                       # Pydantic schemas and data models
│   ├── backend/                      # FastAPI web application
│   │   ├── routes/                   # API endpoints
│   │   ├── services/                 # Business logic layer
│   │   │   ├── chat/                 # Chat and voice orchestration
│   │   │   ├── voice/                # STT/TTS services
│   │   │   ├── audio/                # Audio processing
│   │   │   ├── discord/              # Discord integration
│   │   │   └── llm/                  # Language model services
│   │   ├── dao/                      # Data access objects
│   │   └── utils/                    # Utility functions
│   ├── frontend/                     # Tkinter GUI components
│   ├── training/                     # Voice training pipeline
│   ├── logs/                         # Logging microservice
│   ├── tools/                        # Development tools
│   └── cli/                          # Command-line interface
├── tests/                            # Test suites
│   ├── chatapp/                      # Application tests
│   ├── integration/                  # End-to-end tests
│   └── database/                     # Database test utilities
├── data/                             # Application data
│   ├── audio/                        # Audio files and models
│   ├── training/                     # Training datasets
│   └── logs/                         # Runtime log files
├── config/                           # Configuration files
├── pyproject.toml                    # Modern Python packaging
└── requirements*.txt                 # Dependencies
```

### Core Structure
This is a character interaction and voice training toolkit with three main components:

1. **Backend API** (`src/backend/chat_app/`): FastAPI application handling chat, TTS, and voice services
2. **TTS Training Pipeline** (`src/backend/tts_finetune_app/`): Voice cloning and model fine-tuning workflows
3. **Frontend GUI** (`src/frontend/`): Optional Tkinter debugging interface

### Supporting Infrastructure
- **Logging System** (`src/logs_app/`): Dedicated microservice for structured event logging with error codes and severity levels
- **Testing Framework** (`tests/`): Comprehensive unit and integration tests covering API endpoints, voice pipeline, and WebSocket functionality
- **Constants Management** (`src/constants/` and legacy `constants/`): Centralized path definitions to ensure consistent file locations across services

### Key Backend Services
Located in `src/backend/chat_app/services/`:
- **chat_service.py**: Character persona management and conversation handling
- **voice_service.py**: Audio processing orchestration and STT/TTS coordination
- **whisper_service.py**: Speech-to-text transcription using Whisper models
- **piper_tts_service.py**: Text-to-speech synthesis using Piper models
- **openrouter_service.py**: LLM integration for chat responses

### Event System Architecture
- **Centralized Events**: `src/event_system.py` provides real-time communication via WebSocket
- **Event Types**: System status, chat messages, voice processing, training progress
- **Webhook Support**: External event delivery to registered HTTP endpoints
- **Database Logging**: Events are persisted to SQLite with severity levels

### Configuration Management
- **Settings**: `src/config.py` uses Pydantic for environment-based configuration
- **Paths**: `src/constants/paths.py` defines project-wide path constants
- **Environment**: Copy `.env.example` to `.env` for local configuration overrides

### Database & Persistence
- **SQLite Database**: `src/database.py` handles async operations with aiosqlite
- **Event Logging**: Real-time events stored with timestamps and metadata
- **Training Data**: TTS pipeline stores audio clips, transcripts, and model checkpoints

### TTS Training Pipeline Details
The voice cloning workflow in `src/backend/tts_finetune_app/`:
1. **Ingest**: Audio extraction from MP3/MP4 files
2. **Separation**: Vocal isolation using Spleeter
3. **Segmentation**: Silence-based audio splitting with recursive refinement
4. **Transcription**: Whisper-based transcript generation
5. **Manifest Creation**: Piper-compatible dataset preparation
6. **Training**: Model fine-tuning with checkpoint resumption

### API Structure
- **Base URL**: `http://localhost:8765` (configurable via `API_HOST`/`API_PORT`)
- **Routes**: `/api/chat`, `/api/voice`, `/api/system`, `/api/logs`
- **WebSocket**: `/api/ws` for real-time event streaming
- **Documentation**: `/docs` (OpenAPI/Swagger UI)

## Development Guidelines

### Path Handling
- Use `constants/paths.py` for all project paths
- TTS models: `backend/chat_app/audio/piper_models/`
- Generated audio: `backend/chat_app/audio/generated/`
- Training data: `backend/tts_finetune_app/training_data/`

### Service Integration
- Services communicate via the event system for loose coupling
- Use dependency injection patterns established in `main.py`
- Voice services coordinate through `voice_service.py` orchestrator

### Testing Strategy
- Unit tests: `tests/unit/` for individual components
- Integration tests: `tests/integration/` for API and pipeline workflows
- Test configuration respects CI environment variables

### Code Quality
- Follow existing patterns for error handling with event system integration
- Use type hints consistently (Pydantic models in `models/schemas.py`)
- Maintain async/await patterns for all I/O operations

## Environment Configuration

### Required Environment Variables
- `OPENROUTER_API_KEY`: LLM service authentication (optional, limits chat functionality)
- `API_HOST`/`API_PORT`: Server binding configuration (defaults: localhost:8765)

### Optional Configuration
- `WHISPER_MODEL`: Speech recognition model size (default: "base")
- `PIPER_MODEL_PATH`: TTS model file location
- `LOG_LEVEL`: Logging verbosity (default: "INFO")
- `DEBUG`: Enable development mode features
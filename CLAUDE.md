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
├── tests/                            # Simple test suites (no mocking)
│   ├── test_basic_functionality.py  # Core functionality tests
│   ├── test_api_endpoints.py        # Real API endpoint tests
│   └── test_database_operations.py  # Real database operation tests
├── scripts/                          # Development and debugging scripts
│   ├── debug/                        # Debugging tools for troubleshooting
│   ├── examples/                     # Example and test demonstration scripts
│   ├── interactive/                  # Interactive demos and tools
│   └── voice/                        # Voice processing test scripts
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

### Scripts Organization
The `scripts/` directory contains development and debugging tools:
- **debug/**: Troubleshooting scripts for API errors, database issues, service failures
- **examples/**: Demonstration scripts showing how to use various services
- **interactive/**: Live demos and interactive testing tools
- **voice/**: Audio processing and voice pipeline testing scripts

All scripts include proper Python path setup and can be run from the project root:
```bash
python scripts/debug/debug_db_operations.py
python scripts/examples/test_chat_with_gpt4mini.py
```

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

## Critical Implementation Rules

### NO PLACEHOLDER CODE
- **NEVER** create placeholder implementations in any form
- **NEVER** create stub functions that don't actually work
- **NEVER** create fake/dummy/mock implementations that appear to work but don't
- **ALL** code must be fully functional and working implementations
- If a feature cannot be implemented properly, raise an error or return None rather than fake it
- Services that generate placeholder data (like silent audio files) must be replaced with real implementations

### STRICT NO-FALLBACK POLICY
- **NEVER** create fallback responses that mask service failures
- **NEVER** create methods like `_generate_fallback_response()`, `_create_fallback_audio()`, `_get_fallback_transcription()`, etc.
- **NEVER** return generic template responses when real services fail (e.g., "I hear you regarding '[message]'. I'm here to listen and help.")
- **NEVER** create fake audio files, transcriptions, or responses when services are unavailable
- **ALWAYS** fail fast with proper error codes and meaningful error messages
- **ALWAYS** raise `RuntimeError` or appropriate exceptions when services cannot function
- **ALWAYS** emit error events before raising exceptions for debugging purposes
- **ONLY EXCEPTION**: Hardware fallbacks (CPU vs GPU mode) are acceptable as they represent different operational modes, not masked failures

#### Examples of FORBIDDEN Fallback Patterns:
```python
# ❌ NEVER DO THIS - masks service failure
def generate_response(message):
    try:
        return llm_service.generate(message)
    except Exception:
        return "I hear you regarding that. Let me think about it."

# ❌ NEVER DO THIS - creates fake audio
def generate_tts(text):
    try:
        return tts_service.generate(text)
    except Exception:
        return create_silent_audio_file()

# ✅ CORRECT - fails honestly with proper error
def generate_response(message):
    try:
        return llm_service.generate(message)
    except Exception as e:
        logger.error(f"LLM service failed: {e}")
        raise RuntimeError(f"Chat response generation failed: {e}")
```

### WHY NO FALLBACKS?
- Fallbacks create false confidence in broken systems
- Users get confused by fake responses that don't reflect actual service status
- Debugging becomes impossible when failures are masked
- Applications can't properly handle service outages
- Error conditions go undetected in production
- Services appear to work when they're actually broken

### COST-CONSCIOUS MODEL SELECTION
- **NEVER** use expensive models like Claude-3.5-Sonnet, Claude-3-Opus, GPT-4 Turbo
- **ALWAYS** prioritize FREE models: OpenRouter free tier, Groq, Together AI free models
- **PREFER** cheap models: GPT-4o-mini ($0.15/1M tokens), GPT-3.5-turbo ($0.50/1M tokens)
- **DEFAULT** OpenRouter model: `cognitivecomputations/dolphin-mistral-24b-venice-edition:free`
- **AVOID** Claude models entirely - they are extremely expensive ($3-15/1M tokens)
- **USE** environment variables to override model selection for cost control

#### Current Cheap Model Priority:
1. **FREE**: OpenRouter free models (dolphin-mistral, llama-3.2)  
2. **CHEAP**: GPT-4o-mini, GPT-3.5-turbo
3. **BUDGET**: Groq Llama models, Together AI free tier

### CENTRALIZED MODEL CONFIGURATION
- **SINGLE SOURCE**: All model selection managed in `aichat/backend/services/llm/model_config.py`
- **NO SCATTERED MODELS**: Never define models in individual services anymore
- **COST VISIBILITY**: All models show cost per 1M tokens in logs
- **ENVIRONMENT OVERRIDE**: Use `DEFAULT_LLM_MODEL=openrouter-dolphin-free` in .env to override
- **AUTOMATIC DETECTION**: Detects available API keys and prioritizes cheapest models
- **TIER SYSTEM**: Models categorized as FREE, CHEAP, BUDGET, EXPENSIVE (avoid expensive!)

#### Usage:
```python
from aichat.backend.services.llm.model_config import model_config

# Get the cheapest available model automatically
default_model = model_config.get_default_model()

# Get cost summary for all available models  
print(model_config.get_cost_summary())
```
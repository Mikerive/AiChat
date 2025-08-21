# AI Chat - AI-Powered Chat Application with Voice Cloning

Modern Python package for building AI-powered character agents with voice cloning capabilities. Features a FastAPI backend, optional Tkinter GUI, and comprehensive voice training pipeline.

## Overview
- **Character AI**: Persona management, chat endpoints, conversation memory
- **Voice Training**: Audio ingest → segmentation → transcription → Piper training
- **REST API**: WebSocket event stream for real-time integrations
- **GUI Interface**: Optional Tkinter interface for monitoring and control

## Quick Start

### Prerequisites
- Python 3.8+
- FFmpeg (for audio processing)
- Optional: CUDA-capable GPU for faster inference

### Installation
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate    # Windows
   source venv/bin/activate # macOS/Linux
   ```

3. **Install the package**
   ```bash
   pip install -e .                    # Basic installation
   pip install -e .[dev,gui,training]  # Full installation with all features
   ```

4. **Configure environment** (optional)
   ```bash
   cp .env.example .env
   # Edit .env for API keys and configuration
   ```

### Running the Application

**Start Backend API Server:**
```bash
aichat-backend                           # Basic startup
aichat backend --host 0.0.0.0 --port 8765 --reload  # Development mode
```

**Start GUI Interface:**
```bash
aichat-frontend
```

**Start Training Pipeline:**
```bash
aichat-training --mode serve
```

**CLI Help:**
```bash
aichat --help
```

### API Access
- **OpenAPI docs**: http://localhost:8765/docs
- **WebSocket endpoint**: ws://localhost:8765/api/ws

## Package Structure

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
├── data/                             # Application data
├── config/                           # Configuration files
├── pyproject.toml                    # Modern Python packaging
└── requirements*.txt                 # Dependencies
```

## Key Features

### Voice Training Pipeline
The training system processes audio files through:
1. **Audio ingestion** - Extract and preprocess audio files
2. **Voice separation** - Isolate vocal tracks using Spleeter
3. **Segmentation** - Split audio into training clips
4. **Transcription** - Generate text using Whisper
5. **Training** - Fine-tune Piper TTS models

### API Integration
- RESTful endpoints for chat, voice, and system management
- WebSocket support for real-time events
- OpenRouter integration for LLM responses
- Discord bot integration for voice chat

## Development

### Testing
```bash
pytest                    # Run all tests
pytest -v                # Verbose output
pytest tests/unit        # Run only unit tests
pytest tests/integration # Run only integration tests
```

### Code Quality
```bash
black .                   # Format code
flake8 .                  # Lint code
mypy .                    # Type checking
isort .                   # Sort imports
```

### Development Dependencies
```bash
pip install -r requirements-dev.txt
```

Contributing
1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast (high-performance), web framework for building APIs with Python 3.8+ based on standard Python type hints.
- [Whisper](https://github.com/openai/whisper) - Robust speech recognition by OpenAI
- [Piper](https://github.com/rhasspy/piper) - A fast, local neural text-to-speech system
- [Tkinter](https://docs.python.org/3/library/tkinter.html) - Python's standard GUI toolkit

## Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation at `/docs`

---

**Note**: This is a reimplementation of a VTuber streaming backend. Some features may require additional setup or dependencies for full functionality.
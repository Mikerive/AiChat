# VTuber Backend - Reimplementation

A comprehensive VTuber streaming backend with voice cloning capabilities, real-time chat functionality, and a debugging GUI interface.

## Features

### Core Functionality
- **Real-time Chat Interface**: Interactive chat with AI characters
- **Voice Cloning**: Train custom voice models using your own audio samples
- **Speech-to-Text**: Whisper integration for transcribing audio input
- **Text-to-Speech**: Piper integration for generating natural-sounding speech
- **WebSocket Support**: Real-time updates and event notifications
- **SQLite Database**: Persistent storage for characters, chat logs, and training data

### Debugging & Monitoring
- **Tkinter GUI**: Comprehensive debugging command center
- **Real-time Event System**: Live monitoring of all system events
- **Voice Training Interface**: Upload and manage voice training data
- **System Status Dashboard**: Monitor system health and performance
- **Configuration Management**: Easy configuration through GUI

## Architecture

```
VTuber Backend
├── Backend (FastAPI)
│   ├── API Routes
│   │   ├── Chat Endpoints
│   │   ├── Voice Training Endpoints
│   │   ├── System Endpoints
│   │   └── WebSocket Support
│   ├── Services
│   │   ├── Chat Service
│   │   ├── Whisper Service (STT)
│   │   ├── Voice Service (TTS)
│   │   └── Event System
│   ├── Database (SQLite)
│   └── Configuration
├── Frontend (Tkinter GUI)
│   ├── System Status Tab
│   ├── Chat Interface Tab
│   ├── Voice Training Tab
│   ├── Event Logs Tab
│   └── Configuration Tab
└── Event System
    ├── WebSocket Notifications
    ├── Event Logging
    └── Real-time Updates
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Optional: FFmpeg for audio processing

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd VtuberMiku
   ```

2. **Recommended — use the helper scripts**
   - Linux/macOS (bash):
     ```bash
     ./scripts/create_envs.sh
     ```
   - Windows (PowerShell):
     ```powershell
     .\scripts\create_envs.ps1
     ```
   The helper scripts will create a Python virtual environment at `./venv`, upgrade pip, install packages from [`requirements.txt`](requirements.txt:1), and install local editable packages such as `./backend/chat_app` if present.

3. **Manual (alternative) — create a venv and install requirements**
   ```bash
   python -m venv venv
   source venv/bin/activate    # On Windows (cmd): venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   pip install -e ./backend/chat_app   # for editable development install
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Install optional dependencies for enhanced functionality**
   ```bash
   # For GPU acceleration (optional)
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
   
   # For audio source separation (optional)
   pip install spleeter
   
   # For microphone input (optional)
   pip install pyaudio
   ```

## Usage

### Starting the Application

#### Option 1: Start Both Backend and GUI
```bash
python start_gui.py
```

#### Option 2: Start Backend Only
```bash
python start_gui.py backend
```

#### Option 3: Start GUI Only
```bash
python start_gui.py gui
```

### Accessing the Application

- **GUI Interface**: Launches automatically when starting the application
- **API Documentation**: http://localhost:8765/docs
- **WebSocket Endpoint**: ws://localhost:8765/api/ws

### Configuration

The application can be configured through:

1. **Environment Variables**: Edit `.env` file
2. **GUI Interface**: Use the Configuration tab in the GUI
3. **API Endpoints**: Use `/api/system/config` endpoint

#### Key Configuration Options

```env
# API Configuration
API_HOST=localhost
API_PORT=8765

# Audio Settings
SAMPLE_RATE=16000
CHANNELS=1

# Model Settings
WHISPER_MODEL=base
PIPER_MODEL_PATH=models/piper/en_US-amy-medium.onnx

# Character Settings
CHARACTER_NAME=Miku
CHARACTER_PROFILE=hatsune_miku
CHARACTER_PERSONALITY=cheerful,curious,helpful

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/vtuber.log
```

## API Documentation

### Chat Endpoints

#### Get Characters
```http
GET /api/chat/characters
```

#### Send Chat Message
```http
POST /api/chat
Content-Type: application/json

{
  "text": "Hello, how are you?",
  "character": "hatsune_miku"
}
```

#### Generate TTS
```http
POST /api/tts
Content-Type: application/json

{
  "text": "Hello, world!",
  "character": "hatsune_miku"
}
```

### Voice Training Endpoints

#### Upload Audio
```http
POST /api/voice/upload
Content-Type: multipart/form-data

file: <audio-file>
```

#### Start Training
```http
POST /api/voice/train
Content-Type: application/json

{
  "model_name": "custom_voice",
  "epochs": 10,
  "batch_size": 8
}
```

#### Get Voice Models
```http
GET /api/voice/models
```

### System Endpoints

#### Health Check
```http
GET /health
```

#### Get System Status
```http
GET /api/system/status
```

#### Get Event Logs
```http
GET /api/logs
```

### WebSocket & Events

Connect to the WebSocket endpoint for real-time updates and system events:

```javascript
const ws = new WebSocket('ws://localhost:8765/api/ws');

ws.onopen = () => {
  // Subscribe to specific event-types (optional). If omitted, GUI will receive all events.
  ws.send(JSON.stringify({
    type: "subscribe",
    events: ["audio.transcribed", "audio.captured", "chat.response"]
  }));
};

ws.onmessage = (ev) => {
  const data = JSON.parse(ev.data);
  console.log('Event:', data);
  // Typical event payload from the EventSystem (JSON):
  // {
  //   "id": 123456,
  //   "event_type": "audio.transcribed",
  //   "message": "Speech-to-text transcription completed",
  //   "data": { "stream_id": "local-...", "text": "Hello" },
  //   "severity": "INFO",
  //   "source": null,
  //   "timestamp": "2025-08-17T22:17:31.536Z"
  // }
};
```

WebSocket subscriptions:
- Send a JSON message with `type: "subscribe"` and an `events` array to receive only those events.
- The backend will respect per-client subscriptions and only deliver matching events when present.

Webhook-style event payloads:
- The internal EventSystem uses a consistent JSON schema (see example above). To forward events to your own webhook receiver, POST JSON with the same schema to your endpoint.

Example external webhook receiver (server) expected JSON schema:
```json
{
  "event_type": "chat.response",
  "message": "LLM response generated",
  "data": {
    "stream_id": "local-123",
    "character_response": "Hello!",
    "user_input": "Hi"
  },
  "severity": "INFO",
  "timestamp": "2025-08-17T22:17:31.536Z"
}
```

Note: The GUI connects to the backend WebSocket at `/api/ws` and the REST endpoints under `/api/*` (chat, tts, voice, system). See the API Documentation section above for endpoint details.

## GUI Features

### System Status Tab
- Real-time system monitoring
- Connection status
- Service health checks
- Performance metrics

### Chat Interface Tab
- Character selection
- Chat message input
- TTS generation
- Audio playback controls

### Voice Training Tab
- Audio file upload
- Training progress monitoring
- Voice model management
- Training configuration

### Event Logs Tab
- Real-time event logging
- Event filtering by severity
- Auto-refresh functionality
- Log search capabilities

### Configuration Tab
- API settings
- Audio configuration
- Model settings
- Character configuration

## Development

### Project Structure

```
VtuberMiku/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   ├── routes/            # API route definitions
│   │   └── services/          # Business logic services
│   └── voice_trainer/         # Voice training components
├── frontend/
│   └── gui.py                 # Tkinter GUI application
├── database.py                # Database models and operations
├── event_system.py            # Event system and WebSocket handling
├── config.py                 # Configuration management
├── requirements.txt          # Python dependencies
├── start_gui.py              # Startup script
└── README.md                 # This file
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest

# Run with coverage
pytest --cov=.
```

### Code Style

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   - Change the port in `.env` file
   - Or kill the process using the port: `netstat -ano | findstr :8765`

2. **Audio Processing Errors**
   - Install FFmpeg: `choco install ffmpeg` (Windows) or `sudo apt install ffmpeg` (Linux)
   - Check audio file formats (WAV, MP3, M4A supported)

3. **Model Loading Issues**
   - Ensure model files exist in the specified paths
   - Check disk space for model downloads
   - Verify Python dependencies are installed

4. **WebSocket Connection Issues**
   - Check firewall settings
   - Verify the backend is running
   - Check browser console for errors

### Debug Mode

Enable debug mode for detailed logging:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## Contributing

1. Fork the repository
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
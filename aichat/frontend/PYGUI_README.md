# VTuber PyGui Interface

Modern GPU-accelerated interface for the VTuber backend using Dear PyGui.

## Features

### 🎤 Intensity-First TTS Control
- Real-time intensity visualization with GPU-accelerated plots
- Manual intensity override (0.0-2.0 range)
- Automatic intensity detection from `[INTENSITY: level]` markers
- Live exaggeration level display with human-readable descriptions
- Test TTS generation with character selection

### 💬 Chat Interface  
- Character-based conversations
- Real-time chat history (last 15 messages)
- Auto-TTS generation from chat messages
- Character synchronization between chat and TTS

### 📊 System Status & Monitoring
- Real-time performance metrics (CPU, Memory usage)
- Backend API status monitoring
- Database connection status
- WebSocket connection management
- Live event logs with auto-refresh

### 🔊 Audio Controls
- Hardware detection (PyTorch, CUDA, GPU info)
- Audio device management (input/output)
- Volume control with API integration
- Audio recording and playback testing
- VRAM requirement validation (6GB minimum for GPU)

### ⚙️ Configuration Management
- API settings (host, port)
- TTS voice preferences (speed, pitch)
- Debug mode and auto-connect options
- Refresh interval configuration

## Installation

```bash
# Install required dependencies
pip install dearpygui websocket-client

# Or install from project requirements
pip install -r requirements.txt
```

## Usage

### Direct Launch (Recommended)
```bash
python run_pygui.py
```
*The PyGui interface will automatically start the backend if it's not running.*

### Via CLI
```bash
# Use PyGui interface with auto-backend startup
aichat frontend --gui pygui

# Use traditional Tkinter interface  
aichat frontend --gui tkinter
```

### Backend Management
The PyGui interface includes built-in backend management:

- **Auto-Start**: Automatically detects if backend is running and starts it if needed
- **Manual Controls**: 
  - "Start Backend" - Manually start the backend server
  - "Stop Backend" - Stop the backend server (if started by GUI)
  - "Connect" - Connect/disconnect WebSocket
  - "Restart" - Restart the entire connection

### Via Python Module
```python
from aichat.frontend.pygui_app import VTuberPyGuiApp

app = VTuberPyGuiApp()
app.run()
```

## Architecture

### Component Structure
- **TTS Control Tab**: Intensity-first TTS pipeline with real-time visualization
- **Chat Interface Tab**: Character conversations with history
- **System Status Tab**: Live monitoring and metrics
- **Audio Controls Tab**: Hardware detection and audio management  
- **Configuration Tab**: Settings and preferences

### Real-time Features
- WebSocket integration for live updates
- GPU-accelerated plotting for performance metrics
- Auto-refresh timers for system status
- Thread-safe GUI updates

### API Integration
- FastAPI backend communication
- Pydantic response model validation
- Comprehensive error handling
- Timeout management for long operations

## Intensity-First TTS Pipeline

The PyGui interface provides advanced visualization for the intensity-first streaming pipeline:

1. **Text Input**: Enter text with optional `[INTENSITY: level]` markers
2. **Intensity Detection**: Automatic parsing of intensity levels (flat, low, normal, high, dramatic, theatrical)
3. **Real-time Visualization**: Live plot showing intensity over time
4. **Exaggeration Display**: Current intensity level with human-readable descriptions
5. **Audio Generation**: Consistent intensity applied to all TTS segments

### Intensity Levels
- `flat` (0.0): Monotone/Robotic
- `low` (0.3): Subdued/Quiet  
- `normal` (0.7): Default/Balanced
- `high` (1.2): Energetic/Expressive
- `dramatic` (1.5): Intense/Theatrical
- `theatrical` (2.0): Maximum exaggeration

## Hardware Detection

Automatic detection and optimization:
- **PyTorch Availability**: Checks for PyTorch installation
- **CUDA Support**: Detects GPU availability
- **VRAM Validation**: Ensures 6GB minimum for Chatterbox TTS
- **Performance Mode**: Automatically selects optimal device (GPU/CPU)
- **Graceful Fallback**: CPU-only mode when GPU requirements not met

## Configuration

### API Settings
- Host: Backend server hostname (default: localhost)
- Port: Backend server port (default: 8765)
- Auto-connect: Automatic WebSocket connection on startup

### TTS Settings  
- Default Voice: Voice model selection
- Speed: Speech rate (0.5-2.0)
- Pitch: Voice pitch (0.5-2.0)

### Advanced Settings
- Debug Mode: Enable detailed logging
- Refresh Interval: Status update frequency (100-5000ms)

## Troubleshooting

### Import Errors
```bash
pip install dearpygui websocket-client
```

### Connection Issues
1. **Try the "Start Backend" button** - The PyGui interface can automatically start the backend
2. Check the Event Logs tab for startup messages
3. Verify API settings in Configuration tab (default: localhost:8765)
4. Use "Restart" button to reset the connection

### Performance Issues
1. Check hardware detection results
2. Ensure GPU drivers are updated
3. Monitor system performance metrics

### Unicode/Encoding Issues
The interface handles Windows console encoding automatically and falls back to ASCII-safe messages when needed.

## Development

### Adding New Features
1. Follow existing component structure
2. Use thread-safe GUI updates (`dpg.set_value`)
3. Implement proper error handling with logging
4. Add WebSocket message handlers for real-time updates

### Testing
```bash
# Test PyGui import
python -c "from aichat.frontend.pygui_app import VTuberPyGuiApp; print('PyGui ready')"

# Test with backend integration
aichat backend &  # Start backend
python run_pygui.py  # Start PyGui interface
```
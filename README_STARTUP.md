# VTuber Application Startup Guide

## Quick Start (2 Terminal Method)

### Terminal 1 - Backend Server:
```bash
# Option A: Using Python script
python start_backend.py

# Option B: Using Windows batch file
start_backend.bat

# Option C: Manual command
cd src
python -m uvicorn backend.chat_app.main:create_app --factory --host localhost --port 8765 --reload
```

### Terminal 2 - GUI Application:
```bash
# Option A: Using Python script
python start_gui.py

# Option B: Using Windows batch file  
start_gui.bat

# Option C: Manual command
cd src
python -m frontend.gui
```

## What Each Script Does

### `start_backend.py` / `start_backend.bat`
- Starts the FastAPI backend server on `localhost:8765`
- Includes auto-reload for development
- Handles virtual environment activation (if present)
- Shows clear status messages and error handling

### `start_gui.py` / `start_gui.bat` 
- Starts the Tkinter GUI application
- Connects to the backend server
- Shows system status, chat interface, voice controls, etc.

## Troubleshooting

### Backend Won't Start
1. **Missing dependencies**: `pip install -r requirements.txt`
2. **Port already in use**: Change port in the uvicorn command
3. **Import errors**: Make sure you're in the right directory

### GUI Won't Connect
1. **Backend not running**: Start backend first in separate terminal
2. **Wrong port**: GUI expects backend on `localhost:8765`
3. **Firewall issues**: Check Windows firewall settings

### Common Error: "ModuleNotFoundError"
```bash
# Install missing dependencies
pip install -r requirements.txt

# Or install specific missing packages
pip install librosa uvicorn fastapi pydantic-settings
```

## Development Mode

For development, use the backend with `--reload` flag (included in scripts):
```bash
cd src
python -m uvicorn backend.chat_app.main:create_app --factory --host localhost --port 8765 --reload
```

This automatically restarts the server when code changes are detected.

## Production Mode

For production, remove the `--reload` flag and consider using:
```bash
cd src  
python -m uvicorn backend.chat_app.main:create_app --factory --host 0.0.0.0 --port 8765
```

## File Structure
```
VtuberMiku/
├── start_backend.py    # Backend startup script
├── start_backend.bat   # Windows batch file for backend
├── start_gui.py        # GUI startup script  
├── start_gui.bat       # Windows batch file for GUI
├── requirements.txt    # Python dependencies
└── src/                # Source code directory
    ├── backend/        # Backend API code
    ├── frontend/       # GUI application code
    └── config.py       # Configuration settings
```
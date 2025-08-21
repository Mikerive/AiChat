# AI Chat Application Startup Guide

## Quick Start

### Start Backend Server:
```bash
# Recommended: Using CLI command
aichat-backend

# With custom settings
aichat backend --host localhost --port 8765 --reload

# Alternative: Direct Python module
python -m aichat.cli.backend
```

### Start GUI Application:
```bash
# Using CLI command
aichat-frontend

# Alternative: Direct Python module
python -m aichat.cli.frontend
```

### Start Training Pipeline:
```bash
# Using CLI command
aichat-training --mode serve

# Alternative: Direct Python module
python -m aichat.cli.training
```

## CLI Commands Overview

### `aichat-backend`
- Starts the FastAPI backend server on `localhost:8765`
- Supports custom host, port, and reload options
- Professional logging and error handling
- Built-in help: `aichat backend --help`

### `aichat-frontend`
- Starts the Tkinter GUI application  
- Connects to the backend server automatically
- Shows system status, chat interface, voice controls
- Built-in help: `aichat frontend --help`

### `aichat-training`
- Starts the voice training pipeline
- Supports different modes: ingest, train, serve
- Built-in help: `aichat training --help`

## Troubleshooting

### Package Not Installed
1. **Install package**: `pip install -e .`
2. **Install with dependencies**: `pip install -e .[dev,gui,training]`
3. **Virtual environment**: Make sure your venv is activated

### Backend Won't Start
1. **Missing dependencies**: `pip install -r requirements.txt`
2. **Port already in use**: Use `aichat backend --port 8766`
3. **Import errors**: Ensure package is installed with `pip install -e .`

### GUI Won't Connect
1. **Backend not running**: Start backend first with `aichat-backend`
2. **Wrong port**: GUI expects backend on `localhost:8765`
3. **Package not installed**: Run `pip install -e .[gui]`

### Common Error: "Command not found"
```bash
# Ensure package is installed
pip install -e .

# Check if CLI commands are available
aichat --help

# Alternative: Use Python module syntax
python -m aichat.cli.main --help
```

## Development Mode

For development with auto-reload:
```bash
aichat backend --reload
```

For custom host/port:
```bash
aichat backend --host 0.0.0.0 --port 8765 --reload
```

## Advanced Usage

### Environment Variables
```bash
export API_HOST=localhost
export API_PORT=8765
export OPENROUTER_API_KEY=your_key_here
```

### Package Structure
```bash
aichat/                 # Main package
├── aichat/            # Python package source
├── data/              # Application data
├── config/            # Configuration files
├── tests/             # Test suites
└── pyproject.toml     # Package configuration
```
# Scripts Directory

This directory contains development and testing scripts organized by purpose.

## Directory Structure

### `debug/`
Debugging scripts for troubleshooting specific issues:
- Database operation debugging
- API endpoint debugging  
- Chat service debugging
- Backend crash debugging
- Frontend startup debugging

### `examples/`  
Example and test scripts demonstrating functionality:
- Chat testing with different models
- Database initialization examples
- Audio system testing
- Simple database operations

### `interactive/`
Interactive demonstration scripts:
- Interactive voice demo
- Real-time audio testing

### `voice/`
Voice processing and audio testing scripts:
- Speech pipeline testing
- Streaming audio tests
- TTS/STT testing

## Usage

All scripts should be run from the project root directory:

```bash
cd /path/to/VtuberMiku
python scripts/debug/debug_db_operations.py
python scripts/examples/test_chat_with_gpt4mini.py
python scripts/interactive/interactive_voice_demo.py
python scripts/voice/speech_test.py
```

## Note on Imports

Scripts have been updated to use proper package imports from the project root. Ensure you have the project installed in development mode:

```bash
pip install -e .
```

Or run with PYTHONPATH set:

```bash
PYTHONPATH=. python scripts/debug/debug_db_operations.py
```
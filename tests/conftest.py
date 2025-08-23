"""
Test configuration and fixtures for VTuber backend tests
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Set test environment variables
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_database():
    """Mock database operations"""
    mock_db = AsyncMock()
    mock_db.initialize.return_value = None
    mock_db.close.return_value = None
    mock_db.get_session.return_value.__aenter__.return_value.execute.return_value = None
    return mock_db


@pytest.fixture
def mock_event_system():
    """Mock event system"""
    mock_events = AsyncMock()
    mock_events.emit.return_value = None
    return mock_events


@pytest.fixture(autouse=True)
async def setup_test_environment(mock_database, mock_event_system):
    """Setup test environment with mocked dependencies"""
    with patch('aichat.core.database.get_db', return_value=mock_database), \
         patch('aichat.core.event_system.get_event_system', return_value=mock_event_system):
        yield


class MockAudioDevice:
    """Mock audio device for testing"""
    def __init__(self, id, name, channels=2, sample_rate=44100, is_default=False):
        self.id = id
        self.name = name
        self.channels = channels
        self.sample_rate = sample_rate
        self.is_default = is_default


class MockCharacter:
    """Mock character for testing"""
    def __init__(self, id=1, name="test_character", profile="Test profile", personality="friendly"):
        self.id = id
        self.name = name
        self.profile = profile
        self.personality = personality
        self.avatar_url = "https://example.com/avatar.png"


class MockChatLog:
    """Mock chat log for testing"""
    def __init__(self, id=1, character_id=1, user_message="Hello", character_response="Hi there!"):
        self.id = id
        self.character_id = character_id
        self.user_message = user_message
        self.character_response = character_response
        self.emotion = "happy"
        self.metadata = {"model": "test"}
        from datetime import datetime
        self.timestamp = datetime.now()


@pytest.fixture
def mock_audio_device():
    """Create a mock audio device"""
    return MockAudioDevice(0, "Test Device")


@pytest.fixture
def mock_character():
    """Create a mock character"""
    return MockCharacter()


@pytest.fixture
def mock_chat_log():
    """Create a mock chat log"""
    return MockChatLog()


@pytest.fixture
def sample_audio_file(temp_dir):
    """Create a sample audio file for testing"""
    audio_file = temp_dir / "test_audio.wav"
    
    # Create a minimal WAV file header
    wav_header = bytes([
        0x52, 0x49, 0x46, 0x46,  # "RIFF"
        0x2C, 0x00, 0x00, 0x00,  # File size (44 bytes)
        0x57, 0x41, 0x56, 0x45,  # "WAVE"
        0x66, 0x6D, 0x74, 0x20,  # "fmt "
        0x10, 0x00, 0x00, 0x00,  # Subchunk1Size (16)
        0x01, 0x00,              # AudioFormat (PCM)
        0x01, 0x00,              # NumChannels (1)
        0x44, 0xAC, 0x00, 0x00,  # SampleRate (44100)
        0x88, 0x58, 0x01, 0x00,  # ByteRate (88200)
        0x02, 0x00,              # BlockAlign (2)
        0x10, 0x00,              # BitsPerSample (16)
        0x64, 0x61, 0x74, 0x61,  # "data"
        0x00, 0x00, 0x00, 0x00,  # Subchunk2Size (0)
    ])
    
    with open(audio_file, "wb") as f:
        f.write(wav_header)
    
    return audio_file


# Disable logging during tests to reduce noise
import logging
logging.disable(logging.CRITICAL)
"""
Simple test configuration for VTuber application tests.
"""

import pytest
import os
import tempfile
from pathlib import Path

# Set test environment
os.environ["TESTING"] = "true"

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture  
def sample_audio_file(temp_dir):
    """Create a simple WAV file for testing."""
    audio_file = temp_dir / "test.wav"
    
    # Minimal WAV header
    wav_data = bytes([
        0x52, 0x49, 0x46, 0x46,  # "RIFF"
        0x24, 0x00, 0x00, 0x00,  # File size
        0x57, 0x41, 0x56, 0x45,  # "WAVE"
        0x66, 0x6D, 0x74, 0x20,  # "fmt "
        0x10, 0x00, 0x00, 0x00,  # Subchunk size
        0x01, 0x00,              # PCM format
        0x01, 0x00,              # Mono
        0x44, 0xAC, 0x00, 0x00,  # Sample rate 44100
        0x88, 0x58, 0x01, 0x00,  # Byte rate
        0x02, 0x00,              # Block align
        0x10, 0x00,              # Bits per sample
        0x64, 0x61, 0x74, 0x61,  # "data"
        0x00, 0x00, 0x00, 0x00,  # Data size
    ])
    
    audio_file.write_bytes(wav_data)
    return audio_file
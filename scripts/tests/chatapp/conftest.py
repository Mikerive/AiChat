"""
Shared test configuration for chat_app unit tests.
This file provides common fixtures and test setup for all chat_app unit tests.
"""

import sys
from pathlib import Path
import pytest
import asyncio

# Ensure src/ and tests/ are importable for all chatapp tests
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TESTS = ROOT / "tests"
# Insert src path BEFORE tests path to prioritize main src modules over test modules
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(TESTS) not in sys.path:
    sys.path.insert(1, str(TESTS))

from tests.database import (
    test_db_manager,
    test_db_ops,
    setup_test_database,
    reset_test_database,
)


# Database fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Setup test database for entire test session"""
    await setup_test_database()
    yield
    # Cleanup happens automatically when the test database file is removed


@pytest.fixture(autouse=True)
async def reset_db_for_each_test():
    """Reset database to clean state for each test"""
    await reset_test_database()
    yield


@pytest.fixture
def test_database():
    """Provide access to test database manager"""
    return test_db_manager


@pytest.fixture
def test_db_operations():
    """Provide access to test database operations"""
    return test_db_ops


# Common test data fixtures (using actual test database data)
@pytest.fixture
def sample_character_data():
    """Sample character data for testing (matches test DB)"""
    return {
        "id": 1,
        "name": "hatsune_miku",
        "profile": "A virtual singer and the most popular Vocaloid character. Known for her turquoise twin-tails and cheerful personality.",
        "personality": "cheerful, energetic, loves singing and performing, friendly to fans",
        "avatar_url": "https://example.com/miku.jpg",
    }


@pytest.fixture
def sample_chat_log_data():
    """Sample chat log data for testing (matches test DB)"""
    return {
        "id": 1,
        "character_id": 1,
        "user_message": "Hello Miku! How are you today?",
        "character_response": "Hi there! I'm doing great! I've been practicing some new songs. Would you like to hear about them?",
        "emotion": "happy",
        "metadata": {"model": "gpt-4", "temperature": 0.7, "tokens": 45},
    }


@pytest.fixture
def sample_training_data():
    """Sample training data for testing (matches test DB)"""
    return {
        "id": 1,
        "filename": "miku_sample_01.wav",
        "transcript": "Hello everyone! I'm Hatsune Miku!",
        "duration": 2.5,
        "speaker": "hatsune_miku",
        "emotion": "happy",
        "quality": "high",
    }


@pytest.fixture
def sample_voice_model_data():
    """Sample voice model data for testing (matches test DB)"""
    return {
        "id": 1,
        "name": "hatsune_miku_v1",
        "model_path": "/test/models/miku_v1.onnx",
        "character_id": 1,
        "status": "trained",
        "epochs_trained": 100,
        "loss": 0.025,
    }

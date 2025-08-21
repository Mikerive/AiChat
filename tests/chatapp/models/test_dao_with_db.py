"""
DAO tests using the actual test database.
These tests verify that the DAO operations work correctly with real database data.
"""

import sys
from pathlib import Path
import pytest

# Ensure src/ is importable
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.mark.asyncio
async def test_character_operations_with_test_db(
    test_db_operations, sample_character_data
):
    """Test character database operations using test database"""

    # Test getting existing character by ID
    character = await test_db_operations.get_character(1)
    assert character is not None
    assert character.id == 1
    assert character.name == "hatsune_miku"
    assert character.profile.startswith("A virtual singer")

    # Test getting character by name
    character_by_name = await test_db_operations.get_character_by_name("hatsune_miku")
    assert character_by_name is not None
    assert character_by_name.id == 1
    assert character_by_name.name == "hatsune_miku"

    # Test getting non-existent character
    non_existent = await test_db_operations.get_character(999)
    assert non_existent is None

    # Test listing characters
    characters = await test_db_operations.list_characters()
    assert len(characters) >= 3  # We have 3 sample characters
    assert any(c.name == "hatsune_miku" for c in characters)
    assert any(c.name == "kagamine_rin" for c in characters)
    assert any(c.name == "megurine_luka" for c in characters)


@pytest.mark.asyncio
async def test_chat_log_operations_with_test_db(
    test_db_operations, sample_chat_log_data
):
    """Test chat log database operations using test database"""

    # Test getting all chat logs
    all_logs = await test_db_operations.get_chat_logs()
    assert len(all_logs) >= 4  # We have 4 sample chat logs

    # Test getting chat logs for specific character
    miku_logs = await test_db_operations.get_chat_logs(character_id=1)
    assert len(miku_logs) >= 2  # Miku has at least 2 logs
    for log in miku_logs:
        assert log.character_id == 1

    # Test creating new chat log
    new_log = await test_db_operations.create_chat_log(
        character_id=1,
        user_message="Test message",
        character_response="Test response",
        emotion="neutral",
        metadata={"test": True},
    )
    assert new_log.id is not None

    # Verify the new log was created
    updated_logs = await test_db_operations.get_chat_logs(character_id=1)
    assert len(updated_logs) > len(miku_logs)


@pytest.mark.asyncio
async def test_voice_model_operations_with_test_db(test_db_operations):
    """Test voice model database operations using test database"""

    # Test listing voice models
    models = await test_db_operations.list_voice_models()
    assert len(models) >= 2  # We have 2 sample voice models

    # Check that we have the expected models
    model_names = [m.name for m in models]
    assert "hatsune_miku_v1" in model_names
    assert "kagamine_rin_v1" in model_names

    # Check model properties
    miku_model = next((m for m in models if m.name == "hatsune_miku_v1"), None)
    assert miku_model is not None
    assert miku_model.character_id == 1
    assert miku_model.status == "trained"


@pytest.mark.asyncio
async def test_training_data_operations_with_test_db(
    test_db_operations, sample_training_data
):
    """Test training data database operations using test database"""

    # Test listing training data
    training_data = await test_db_operations.list_training_data()
    assert len(training_data) >= 3  # We have 3 sample training data entries

    # Check expected files
    filenames = [td.filename for td in training_data]
    assert "miku_sample_01.wav" in filenames
    assert "miku_sample_02.wav" in filenames
    assert "rin_sample_01.wav" in filenames

    # Check training data properties
    miku_sample = next(
        (td for td in training_data if td.filename == "miku_sample_01.wav"), None
    )
    assert miku_sample is not None
    assert miku_sample.speaker == "hatsune_miku"
    assert miku_sample.transcript == "Hello everyone! I'm Hatsune Miku!"
    assert miku_sample.duration == 2.5

    # Test creating new training data
    new_training_data = await test_db_operations.create_training_data(
        filename="test_sample.wav",
        transcript="This is a test",
        duration=1.5,
        speaker="hatsune_miku",
        quality="high",
    )
    assert new_training_data.id is not None
    assert new_training_data.filename == "test_sample.wav"


@pytest.mark.asyncio
async def test_database_relationships(test_db_operations):
    """Test that database relationships work correctly"""

    # Get Miku's character record
    miku = await test_db_operations.get_character_by_name("hatsune_miku")
    assert miku is not None

    # Get Miku's chat logs
    miku_logs = await test_db_operations.get_chat_logs(character_id=miku.id)
    assert len(miku_logs) > 0

    # Get Miku's voice models
    all_models = await test_db_operations.list_voice_models()
    miku_models = [m for m in all_models if m.character_id == miku.id]
    assert len(miku_models) > 0

    # Get Miku's training data
    all_training_data = await test_db_operations.list_training_data()
    miku_training_data = [
        td for td in all_training_data if td.speaker == "hatsune_miku"
    ]
    assert len(miku_training_data) > 0


@pytest.mark.asyncio
async def test_database_data_integrity(test_db_operations):
    """Test that the test database contains the expected sample data"""

    # Verify all expected characters exist
    expected_characters = ["hatsune_miku", "kagamine_rin", "megurine_luka"]
    characters = await test_db_operations.list_characters()
    character_names = [c.name for c in characters]

    for expected_name in expected_characters:
        assert (
            expected_name in character_names
        ), f"Expected character {expected_name} not found"

    # Verify chat logs exist for different characters
    all_logs = await test_db_operations.get_chat_logs()
    character_ids_in_logs = set(log.character_id for log in all_logs)
    assert (
        len(character_ids_in_logs) >= 3
    ), "Expected chat logs for at least 3 different characters"

    # Verify training data exists for different speakers
    training_data = await test_db_operations.list_training_data()
    speakers = set(td.speaker for td in training_data)
    assert "hatsune_miku" in speakers
    assert "kagamine_rin" in speakers

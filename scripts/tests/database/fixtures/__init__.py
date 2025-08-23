"""
Test database fixtures.
Contains JSON files with sample data for database population.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

FIXTURES_DIR = Path(__file__).parent


def load_fixture(fixture_name: str) -> List[Dict[str, Any]]:
    """Load fixture data from JSON file"""
    fixture_path = FIXTURES_DIR / f"{fixture_name}.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_fixtures() -> Dict[str, List[Dict[str, Any]]]:
    """Load all fixture data"""
    fixtures = {}

    fixture_files = [
        "characters",
        "chat_logs",
        "training_data",
        "voice_models",
        "event_logs",
    ]

    for fixture_name in fixture_files:
        fixtures[fixture_name] = load_fixture(fixture_name)

    return fixtures


# Convenience exports for backward compatibility
def get_sample_characters() -> List[Dict[str, Any]]:
    """Get sample character data"""
    return load_fixture("characters")


def get_sample_chat_logs() -> List[Dict[str, Any]]:
    """Get sample chat log data"""
    return load_fixture("chat_logs")


def get_sample_training_data() -> List[Dict[str, Any]]:
    """Get sample training data"""
    return load_fixture("training_data")


def get_sample_voice_models() -> List[Dict[str, Any]]:
    """Get sample voice model data"""
    return load_fixture("voice_models")


def get_sample_event_logs() -> List[Dict[str, Any]]:
    """Get sample event log data"""
    return load_fixture("event_logs")

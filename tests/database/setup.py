"""
Test database setup and utilities.
This module provides a dedicated test database with sample data for tests.
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

TEST_DB_PATH = Path(__file__).parent / "test_data.db"

# Load sample data from JSON fixtures
from .fixtures import (
    get_sample_characters,
    get_sample_chat_logs,
    get_sample_training_data,
    get_sample_voice_models,
    get_sample_event_logs,
)


def create_test_database():
    """Create and populate the test database with sample data"""
    # Remove existing test database
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    # Create database and tables
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()

    # Create tables
    create_tables(cursor)

    # Insert sample data
    insert_sample_data(cursor)

    conn.commit()
    conn.close()

    print(f"Test database created at: {TEST_DB_PATH}")


def create_tables(cursor):
    """Create database tables"""
    # Characters table
    cursor.execute(
        """
        CREATE TABLE characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            profile TEXT NOT NULL,
            personality TEXT NOT NULL,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Chat logs table
    cursor.execute(
        """
        CREATE TABLE chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            user_message TEXT NOT NULL,
            character_response TEXT NOT NULL,
            emotion TEXT,
            metadata TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (character_id) REFERENCES characters (id)
        )
    """
    )

    # Training data table
    cursor.execute(
        """
        CREATE TABLE training_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            transcript TEXT,
            duration REAL,
            speaker TEXT NOT NULL,
            emotion TEXT,
            quality TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Voice models table
    cursor.execute(
        """
        CREATE TABLE voice_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            model_path TEXT NOT NULL,
            character_id INTEGER,
            status TEXT NOT NULL,
            epochs_trained INTEGER,
            loss REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (character_id) REFERENCES characters (id)
        )
    """
    )

    # Event logs table
    cursor.execute(
        """
        CREATE TABLE event_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            data TEXT,
            severity TEXT NOT NULL,
            source TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create indexes
    indexes = [
        "CREATE INDEX idx_chat_logs_character_id ON chat_logs (character_id)",
        "CREATE INDEX idx_chat_logs_timestamp ON chat_logs (timestamp)",
        "CREATE INDEX idx_training_data_speaker ON training_data (speaker)",
        "CREATE INDEX idx_voice_models_status ON voice_models (status)",
        "CREATE INDEX idx_event_logs_event_type ON event_logs (event_type)",
        "CREATE INDEX idx_event_logs_timestamp ON event_logs (timestamp)",
    ]

    for index in indexes:
        cursor.execute(index)


def insert_sample_data(cursor):
    """Insert sample data into tables"""
    # Load data from JSON fixtures
    characters = get_sample_characters()
    chat_logs = get_sample_chat_logs()
    training_data = get_sample_training_data()
    voice_models = get_sample_voice_models()
    event_logs = get_sample_event_logs()

    # Insert characters
    for char in characters:
        cursor.execute(
            """
            INSERT INTO characters (id, name, profile, personality, avatar_url)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                char["id"],
                char["name"],
                char["profile"],
                char["personality"],
                char["avatar_url"],
            ),
        )

    # Insert chat logs with timestamps
    base_time = datetime.now() - timedelta(days=1)
    for i, log in enumerate(chat_logs):
        timestamp = base_time + timedelta(hours=i)
        cursor.execute(
            """
            INSERT INTO chat_logs (id, character_id, user_message, character_response, emotion, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                log["id"],
                log["character_id"],
                log["user_message"],
                log["character_response"],
                log["emotion"],
                json.dumps(log["metadata"]),
                timestamp.isoformat(),
            ),
        )

    # Insert training data
    for data in training_data:
        cursor.execute(
            """
            INSERT INTO training_data (id, filename, transcript, duration, speaker, emotion, quality)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                data["id"],
                data["filename"],
                data["transcript"],
                data["duration"],
                data["speaker"],
                data["emotion"],
                data["quality"],
            ),
        )

    # Insert voice models
    for model in voice_models:
        cursor.execute(
            """
            INSERT INTO voice_models (id, name, model_path, character_id, status, epochs_trained, loss)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                model["id"],
                model["name"],
                model["model_path"],
                model["character_id"],
                model["status"],
                model["epochs_trained"],
                model["loss"],
            ),
        )

    # Insert event logs with recent timestamps
    base_event_time = datetime.now() - timedelta(minutes=30)
    for i, event in enumerate(event_logs):
        timestamp = base_event_time + timedelta(minutes=i * 5)
        cursor.execute(
            """
            INSERT INTO event_logs (id, event_type, message, data, severity, source, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event["id"],
                event["event_type"],
                event["message"],
                json.dumps(event["data"]),
                event["severity"],
                event["source"],
                timestamp.isoformat(),
            ),
        )


def get_test_db_path() -> Path:
    """Get the path to the test database"""
    return TEST_DB_PATH


def cleanup_test_database():
    """Remove the test database"""
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
        print("Test database cleaned up")


if __name__ == "__main__":
    create_test_database()
    print("Test database setup complete!")

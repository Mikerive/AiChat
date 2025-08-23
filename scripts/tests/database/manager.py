"""
Test database manager for use in unit tests.
This provides a clean database connection for each test run.
"""

import asyncio
import aiosqlite
import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator

from .setup import get_test_db_path, create_test_database


class TestDatabaseManager:
    """Database manager specifically for tests"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_test_db_path()
        self._initialized = False

    async def initialize(self):
        """Initialize test database"""
        if not self.db_path.exists():
            create_test_database()
        self._initialized = True

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get database session"""
        if not self._initialized:
            await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db

    async def reset_database(self):
        """Reset database to initial state"""
        if self.db_path.exists():
            self.db_path.unlink()
        create_test_database()
        self._initialized = True


class TestDBOperations:
    """Test database operations that match the production interface"""

    def __init__(self, db_manager: TestDatabaseManager):
        self.db_manager = db_manager

    async def get_character(self, character_id: int):
        """Get character by ID"""
        async with self.db_manager.get_session() as db:
            cursor = await db.execute(
                "SELECT * FROM characters WHERE id = ?", (character_id,)
            )
            row = await cursor.fetchone()
            if row:
                return type(
                    "Character",
                    (),
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "profile": row["profile"],
                        "personality": row["personality"],
                        "avatar_url": row["avatar_url"],
                    },
                )()
            return None

    async def get_character_by_name(self, name: str):
        """Get character by name"""
        async with self.db_manager.get_session() as db:
            cursor = await db.execute(
                "SELECT * FROM characters WHERE name = ?", (name,)
            )
            row = await cursor.fetchone()
            if row:
                return type(
                    "Character",
                    (),
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "profile": row["profile"],
                        "personality": row["personality"],
                        "avatar_url": row["avatar_url"],
                    },
                )()
            return None

    async def list_characters(self, limit: int = 100):
        """List all characters"""
        characters = []
        async with self.db_manager.get_session() as db:
            cursor = await db.execute(
                "SELECT * FROM characters ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            async for row in cursor:
                characters.append(
                    type(
                        "Character",
                        (),
                        {
                            "id": row["id"],
                            "name": row["name"],
                            "profile": row["profile"],
                            "personality": row["personality"],
                            "avatar_url": row["avatar_url"],
                        },
                    )()
                )
        return characters

    async def create_chat_log(
        self,
        character_id: int,
        user_message: str,
        character_response: str,
        emotion: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Create a chat log entry"""
        async with self.db_manager.get_session() as db:
            cursor = await db.execute(
                """
                INSERT INTO chat_logs (character_id, user_message, character_response, emotion, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    character_id,
                    user_message,
                    character_response,
                    emotion,
                    json.dumps(metadata) if metadata else None,
                ),
            )

            log_id = cursor.lastrowid
            await db.commit()

            return type("ChatLog", (), {"id": log_id})()

    async def get_chat_logs(self, character_id: Optional[int] = None, limit: int = 100):
        """Get chat logs"""
        logs = []
        async with self.db_manager.get_session() as db:
            if character_id:
                cursor = await db.execute(
                    """
                    SELECT * FROM chat_logs WHERE character_id = ? 
                    ORDER BY timestamp DESC LIMIT ?
                """,
                    (character_id, limit),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM chat_logs ORDER BY timestamp DESC LIMIT ?
                """,
                    (limit,),
                )

            async for row in cursor:
                logs.append(
                    type(
                        "ChatLog",
                        (),
                        {
                            "id": row["id"],
                            "character_id": row["character_id"],
                            "user_message": row["user_message"],
                            "character_response": row["character_response"],
                            "emotion": row["emotion"],
                            "metadata": (
                                json.loads(row["metadata"]) if row["metadata"] else {}
                            ),
                            "timestamp": row["timestamp"],
                        },
                    )()
                )
        return logs

    async def list_voice_models(self, limit: int = 100):
        """List voice models"""
        models = []
        async with self.db_manager.get_session() as db:
            cursor = await db.execute(
                "SELECT * FROM voice_models ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            async for row in cursor:
                models.append(
                    type(
                        "VoiceModel",
                        (),
                        {
                            "id": row["id"],
                            "name": row["name"],
                            "model_path": row["model_path"],
                            "character_id": row["character_id"],
                            "status": row["status"],
                        },
                    )()
                )
        return models

    async def list_training_data(self, limit: int = 100):
        """List training data"""
        data = []
        async with self.db_manager.get_session() as db:
            cursor = await db.execute(
                "SELECT * FROM training_data ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            async for row in cursor:
                data.append(
                    type(
                        "TrainingData",
                        (),
                        {
                            "id": row["id"],
                            "filename": row["filename"],
                            "transcript": row["transcript"],
                            "duration": row["duration"],
                            "speaker": row["speaker"],
                        },
                    )()
                )
        return data

    async def create_training_data(
        self,
        filename: str,
        transcript: Optional[str] = None,
        duration: Optional[float] = None,
        speaker: Optional[str] = None,
        quality: Optional[str] = None,
    ):
        """Create training data entry"""
        async with self.db_manager.get_session() as db:
            cursor = await db.execute(
                """
                INSERT INTO training_data (filename, transcript, duration, speaker, quality)
                VALUES (?, ?, ?, ?, ?)
            """,
                (filename, transcript, duration, speaker, quality),
            )

            data_id = cursor.lastrowid
            await db.commit()

            return type("TrainingData", (), {"id": data_id, "filename": filename})()


# Global test database manager and operations
test_db_manager = TestDatabaseManager()
test_db_ops = TestDBOperations(test_db_manager)


async def setup_test_database():
    """Setup test database for test session"""
    await test_db_manager.initialize()


async def cleanup_test_database():
    """Cleanup test database after test session"""
    if test_db_manager.db_path.exists():
        test_db_manager.db_path.unlink()


async def reset_test_database():
    """Reset test database to initial state"""
    await test_db_manager.reset_database()

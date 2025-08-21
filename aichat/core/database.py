"""
Database module for SQLite operations
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional
from pathlib import Path

# aiosqlite is an optional runtime dependency used when running the app with an async DB.
# In test environments it may not be installed; avoid ImportError at import-time so tests can import modules.
try:
    import aiosqlite  # type: ignore
except Exception:
    aiosqlite = None  # type: ignore

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# Database models
class Character(BaseModel):
    """Character model"""

    id: Optional[int] = None
    name: str
    profile: str
    personality: str
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChatLog(BaseModel):
    """Chat log model"""

    id: Optional[int] = None
    character_id: int
    user_message: str
    character_response: str
    emotion: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None


class TrainingData(BaseModel):
    """Training data model"""

    id: Optional[int] = None
    filename: str
    transcript: Optional[str] = None
    duration: Optional[float] = None
    speaker: str
    emotion: Optional[str] = None
    quality: Optional[str] = None
    created_at: Optional[datetime] = None


class VoiceModel(BaseModel):
    """Voice model model"""

    id: Optional[int] = None
    name: str
    model_path: str
    character_id: Optional[int] = None
    status: str
    epochs_trained: Optional[int] = None
    loss: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EventLog(BaseModel):
    """Event log model"""

    id: Optional[int] = None
    event_type: str
    message: str
    data: Optional[Dict[str, Any]] = None
    severity: str
    source: Optional[str] = None
    timestamp: Optional[datetime] = None


class DatabaseManager:
    """Database manager for SQLite operations"""

    def __init__(self, db_path: str = "vtuber.db"):
        self.db_path = db_path
        self._initialized = False

    async def initialize(self):
        """Initialize database and create tables"""
        try:
            # Create database directory
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.db_path) as db:
                # Create tables
                await self._create_tables(db)

                # Create indexes
                await self._create_indexes(db)

                self._initialized = True
                logger.info(f"Database initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    async def _create_tables(self, db: Any):
        """Create database tables"""
        # Characters table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS characters (
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
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_logs (
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
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS training_data (
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
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS voice_models (
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
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS event_logs (
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

        await db.commit()

    async def _create_indexes(self, db: Any):
        """Create database indexes"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_chat_logs_character_id ON chat_logs (character_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_logs_timestamp ON chat_logs (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_training_data_speaker ON training_data (speaker)",
            "CREATE INDEX IF NOT EXISTS idx_voice_models_status ON voice_models (status)",
            "CREATE INDEX IF NOT EXISTS idx_event_logs_event_type ON event_logs (event_type)",
            "CREATE INDEX IF NOT EXISTS idx_event_logs_timestamp ON event_logs (timestamp)",
        ]

        for index in indexes:
            await db.execute(index)

        await db.commit()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[Any, None]:
        """Get database session

        Note: If aiosqlite is not installed, this will raise at runtime when attempting to
        establish a connection. Tests that merely import this module will not hit that code path.
        """
        if not self._initialized:
            await self.initialize()

        if aiosqlite is None:
            raise RuntimeError(
                "aiosqlite is not installed; async database operations are unavailable in this environment"
            )

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db

    async def close(self):
        """Close database connections"""
        # SQLite connections are automatically closed when the context manager exits


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> DatabaseManager:
    """Return the global DatabaseManager instance (compat shim)."""
    return db_manager


# Database operations
async def create_character(
    name: str, profile: str, personality: str, avatar_url: Optional[str] = None
) -> Character:
    """Create a new character"""
    try:
        async with db_manager.get_session() as db:
            cursor = await db.execute(
                "INSERT INTO characters (name, profile, personality, avatar_url) VALUES (?, ?, ?, ?)",
                (name, profile, personality, avatar_url),
            )
            character_id = cursor.lastrowid

            # Get created character
            cursor = await db.execute(
                "SELECT * FROM characters WHERE id = ?", (character_id,)
            )
            row = await cursor.fetchone()

            return Character(
                id=row["id"],
                name=row["name"],
                profile=row["profile"],
                personality=row["personality"],
                avatar_url=row["avatar_url"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    except Exception as e:
        logger.error(f"Error creating character: {e}")
        raise


async def get_character(character_id: int) -> Optional[Character]:
    """Get character by ID"""
    try:
        async with db_manager.get_session() as db:
            cursor = await db.execute(
                "SELECT * FROM characters WHERE id = ?", (character_id,)
            )
            row = await cursor.fetchone()

            if row:
                return Character(
                    id=row["id"],
                    name=row["name"],
                    profile=row["profile"],
                    personality=row["personality"],
                    avatar_url=row["avatar_url"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
            return None

    except Exception as e:
        logger.error(f"Error getting character: {e}")
        raise


async def get_character_by_name(name: str) -> Optional[Character]:
    """Get character by name"""
    try:
        async with db_manager.get_session() as db:
            cursor = await db.execute(
                "SELECT * FROM characters WHERE name = ?", (name,)
            )
            row = await cursor.fetchone()

            if row:
                return Character(
                    id=row["id"],
                    name=row["name"],
                    profile=row["profile"],
                    personality=row["personality"],
                    avatar_url=row["avatar_url"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
            return None

    except Exception as e:
        logger.error(f"Error getting character by name: {e}")
        raise


async def list_characters(limit: int = 100) -> List[Character]:
    """List all characters"""
    try:
        characters = []
        async with db_manager.get_session() as db:
            cursor = await db.execute(
                "SELECT * FROM characters ORDER BY created_at DESC LIMIT ?", (limit,)
            )

            for row in await cursor.fetchall():
                characters.append(
                    Character(
                        id=row["id"],
                        name=row["name"],
                        profile=row["profile"],
                        personality=row["personality"],
                        avatar_url=row["avatar_url"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                    )
                )

        return characters

    except Exception as e:
        logger.error(f"Error listing characters: {e}")
        raise


async def create_chat_log(
    character_id: int,
    user_message: str,
    character_response: str,
    emotion: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ChatLog:
    """Create a new chat log entry"""
    try:
        async with db_manager.get_session() as db:
            cursor = await db.execute(
                "INSERT INTO chat_logs (character_id, user_message, character_response, emotion, metadata) VALUES (?, ?, ?, ?, ?)",
                (
                    character_id,
                    user_message,
                    character_response,
                    emotion,
                    str(metadata) if metadata else None,
                ),
            )
            log_id = cursor.lastrowid

            # Get created log
            cursor = await db.execute("SELECT * FROM chat_logs WHERE id = ?", (log_id,))
            row = await cursor.fetchone()

            return ChatLog(
                id=row["id"],
                character_id=row["character_id"],
                user_message=row["user_message"],
                character_response=row["character_response"],
                emotion=row["emotion"],
                metadata=eval(row["metadata"]) if row["metadata"] else None,
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )

    except Exception as e:
        logger.error(f"Error creating chat log: {e}")
        raise


async def get_chat_logs(
    character_id: Optional[int] = None, limit: int = 100
) -> List[ChatLog]:
    """Get chat logs"""
    try:
        logs = []
        async with db_manager.get_session() as db:
            if character_id:
                cursor = await db.execute(
                    "SELECT * FROM chat_logs WHERE character_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (character_id, limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM chat_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
                )

            for row in await cursor.fetchall():
                logs.append(
                    ChatLog(
                        id=row["id"],
                        character_id=row["character_id"],
                        user_message=row["user_message"],
                        character_response=row["character_response"],
                        emotion=row["emotion"],
                        metadata=eval(row["metadata"]) if row["metadata"] else None,
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                    )
                )

        return logs

    except Exception as e:
        logger.error(f"Error getting chat logs: {e}")
        raise


async def create_training_data(
    filename: str,
    transcript: Optional[str] = None,
    duration: Optional[float] = None,
    speaker: str = "unknown",
    emotion: Optional[str] = None,
    quality: Optional[str] = None,
) -> TrainingData:
    """Create a new training data entry"""
    try:
        async with db_manager.get_session() as db:
            cursor = await db.execute(
                "INSERT INTO training_data (filename, transcript, duration, speaker, emotion, quality) VALUES (?, ?, ?, ?, ?, ?)",
                (filename, transcript, duration, speaker, emotion, quality),
            )
            data_id = cursor.lastrowid

            # Get created entry
            cursor = await db.execute(
                "SELECT * FROM training_data WHERE id = ?", (data_id,)
            )
            row = await cursor.fetchone()

            return TrainingData(
                id=row["id"],
                filename=row["filename"],
                transcript=row["transcript"],
                duration=row["duration"],
                speaker=row["speaker"],
                emotion=row["emotion"],
                quality=row["quality"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    except Exception as e:
        logger.error(f"Error creating training data: {e}")
        raise


async def list_training_data(limit: int = 100) -> List[TrainingData]:
    """List training data"""
    try:
        data = []
        async with db_manager.get_session() as db:
            cursor = await db.execute(
                "SELECT * FROM training_data ORDER BY created_at DESC LIMIT ?", (limit,)
            )

            for row in await cursor.fetchall():
                data.append(
                    TrainingData(
                        id=row["id"],
                        filename=row["filename"],
                        transcript=row["transcript"],
                        duration=row["duration"],
                        speaker=row["speaker"],
                        emotion=row["emotion"],
                        quality=row["quality"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                    )
                )

        return data

    except Exception as e:
        logger.error(f"Error listing training data: {e}")
        raise


async def create_voice_model(
    name: str,
    model_path: str,
    character_id: Optional[int] = None,
    status: str = "created",
    epochs_trained: Optional[int] = None,
    loss: Optional[float] = None,
) -> VoiceModel:
    """Create a new voice model"""
    try:
        async with db_manager.get_session() as db:
            cursor = await db.execute(
                "INSERT INTO voice_models (name, model_path, character_id, status, epochs_trained, loss) VALUES (?, ?, ?, ?, ?, ?)",
                (name, model_path, character_id, status, epochs_trained, loss),
            )
            model_id = cursor.lastrowid

            # Get created model
            cursor = await db.execute(
                "SELECT * FROM voice_models WHERE id = ?", (model_id,)
            )
            row = await cursor.fetchone()

            return VoiceModel(
                id=row["id"],
                name=row["name"],
                model_path=row["model_path"],
                character_id=row["character_id"],
                status=row["status"],
                epochs_trained=row["epochs_trained"],
                loss=row["loss"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    except Exception as e:
        logger.error(f"Error creating voice model: {e}")
        raise


async def list_voice_models(limit: int = 100) -> List[VoiceModel]:
    """List voice models"""
    try:
        models = []
        async with db_manager.get_session() as db:
            cursor = await db.execute(
                "SELECT * FROM voice_models ORDER BY created_at DESC LIMIT ?", (limit,)
            )

            for row in await cursor.fetchall():
                models.append(
                    VoiceModel(
                        id=row["id"],
                        name=row["name"],
                        model_path=row["model_path"],
                        character_id=row["character_id"],
                        status=row["status"],
                        epochs_trained=row["epochs_trained"],
                        loss=row["loss"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                    )
                )

        return models

    except Exception as e:
        logger.error(f"Error listing voice models: {e}")
        raise


async def log_event(
    event_type: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    severity: str = "INFO",
    source: Optional[str] = None,
) -> EventLog:
    """Log an event"""
    try:
        async with db_manager.get_session() as db:
            cursor = await db.execute(
                "INSERT INTO event_logs (event_type, message, data, severity, source) VALUES (?, ?, ?, ?, ?)",
                (event_type, message, str(data) if data else None, severity, source),
            )
            event_id = cursor.lastrowid

            # Get created event
            cursor = await db.execute(
                "SELECT * FROM event_logs WHERE id = ?", (event_id,)
            )
            row = await cursor.fetchone()

            return EventLog(
                id=row["id"],
                event_type=row["event_type"],
                message=row["message"],
                data=eval(row["data"]) if row["data"] else None,
                severity=row["severity"],
                source=row["source"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )

    except Exception as e:
        logger.error(f"Error logging event: {e}")
        raise


# Convenience functions for database operations
# Wrap functions as static methods on a simple object so they don't receive a bound 'self'
_db_ops_attrs = {
    "create_character": staticmethod(create_character),
    "get_character": staticmethod(get_character),
    "get_character_by_name": staticmethod(get_character_by_name),
    "list_characters": staticmethod(list_characters),
    "create_chat_log": staticmethod(create_chat_log),
    "get_chat_logs": staticmethod(get_chat_logs),
    "create_training_data": staticmethod(create_training_data),
    "list_training_data": staticmethod(list_training_data),
    "create_voice_model": staticmethod(create_voice_model),
    "list_voice_models": staticmethod(list_voice_models),
    "log_event": staticmethod(log_event),
    "db_manager": db_manager,
}
db_ops = type("DatabaseOperations", (), _db_ops_attrs)()

# If aiosqlite is not available (test environments), provide a simple in-memory async-backed shim
# so higher-level services can import and operate without requiring the real DB.
if aiosqlite is None:
    from datetime import datetime as _dt

    _in_memory_db = {
        "characters": [],
        "training_data": [],
        "voice_models": [],
        "chat_logs": [],
        "event_logs": [],
    }
    _id_counters = {
        "characters": 1,
        "training_data": 1,
        "voice_models": 1,
        "chat_logs": 1,
        "event_logs": 1,
    }

    async def _create_character(
        name: str, profile: str, personality: str, avatar_url: Optional[str] = None
    ) -> Character:
        cid = _id_counters["characters"]
        _id_counters["characters"] += 1
        now = _dt.utcnow()
        ch = Character(
            id=cid,
            name=name,
            profile=profile,
            personality=personality,
            avatar_url=avatar_url,
            created_at=now,
            updated_at=now,
        )
        _in_memory_db["characters"].append(ch)
        return ch

    async def _get_character(character_id: int) -> Optional[Character]:
        for c in _in_memory_db["characters"]:
            if c.id == character_id:
                return c
        return None

    async def _get_character_by_name(name: str) -> Optional[Character]:
        for c in _in_memory_db["characters"]:
            if c.name == name:
                return c
        return None

    async def _list_characters(limit: int = 100) -> List[Character]:
        return list(_in_memory_db["characters"][:limit])

    async def _create_training_data(
        filename: str,
        transcript: Optional[str] = None,
        duration: Optional[float] = None,
        speaker: str = "unknown",
        emotion: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> TrainingData:
        did = _id_counters["training_data"]
        _id_counters["training_data"] += 1
        now = _dt.utcnow()
        td = TrainingData(
            id=did,
            filename=filename,
            transcript=transcript,
            duration=duration,
            speaker=speaker,
            emotion=emotion,
            quality=quality,
            created_at=now,
        )
        _in_memory_db["training_data"].append(td)
        return td

    async def _list_training_data(limit: int = 100) -> List[TrainingData]:
        return list(_in_memory_db["training_data"][:limit])

    async def _list_voice_models(limit: int = 100) -> List[VoiceModel]:
        return list(_in_memory_db["voice_models"][:limit])

    async def _get_chat_logs(
        character_id: Optional[int] = None, limit: int = 100
    ) -> List[ChatLog]:
        logs = []
        for row in _in_memory_db["chat_logs"]:
            if character_id is None or row.character_id == character_id:
                logs.append(row)
        return logs[:limit]

    async def _create_chat_log(
        character_id: int,
        user_message: str,
        character_response: str,
        emotion: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatLog:
        lid = _id_counters["chat_logs"]
        _id_counters["chat_logs"] += 1
        now = _dt.utcnow()
        cl = ChatLog(
            id=lid,
            character_id=character_id,
            user_message=user_message,
            character_response=character_response,
            emotion=emotion,
            metadata=metadata,
            timestamp=now,
        )
        _in_memory_db["chat_logs"].append(cl)
        return cl

    # Rebuild db_ops shim to use in-memory implementations
    _db_ops_attrs = {
        "create_character": staticmethod(_create_character),
        "get_character": staticmethod(_get_character),
        "get_character_by_name": staticmethod(_get_character_by_name),
        "list_characters": staticmethod(_list_characters),
        "create_chat_log": staticmethod(_create_chat_log),
        "get_chat_logs": staticmethod(_get_chat_logs),
        "create_training_data": staticmethod(_create_training_data),
        "list_training_data": staticmethod(_list_training_data),
        "create_voice_model": staticmethod(lambda *args, **kwargs: None),
        "list_voice_models": staticmethod(_list_voice_models),
        "log_event": staticmethod(lambda *args, **kwargs: None),
        "db_manager": db_manager,
    }
    db_ops = type("DatabaseOperations", (), _db_ops_attrs)()

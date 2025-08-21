"""
Chat Log Data Access Object

Handles database operations for chat conversation history.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from aichat.core.database import ChatLog

from .base_dao import BaseDAO


class ChatLogDAO(BaseDAO):
    """DAO for chat log CRUD operations"""

    async def create_chat_log(
        self,
        character_id: int,
        user_message: str,
        character_response: str,
        emotion: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatLog:
        """Create a new chat log entry"""
        import json

        query = """
        INSERT INTO chat_logs (character_id, user_message, character_response, emotion, metadata, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        now = datetime.now()
        metadata_json = json.dumps(metadata) if metadata else None
        params = (
            character_id,
            user_message,
            character_response,
            emotion,
            metadata_json,
            now,
        )

        async with self.get_connection() as db:
            cursor = await db.execute(query, params)
            await db.commit()
            log_id = cursor.lastrowid

        return ChatLog(
            id=log_id,
            character_id=character_id,
            user_message=user_message,
            character_response=character_response,
            emotion=emotion,
            metadata=metadata,
            timestamp=now,
        )

    async def get_chat_logs(
        self, character_id: Optional[int] = None, limit: int = 100
    ) -> List[ChatLog]:
        """Get chat logs, optionally filtered by character"""
        if character_id:
            query = """
            SELECT * FROM chat_logs
            WHERE character_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """
            params = (character_id, limit)
        else:
            query = "SELECT * FROM chat_logs ORDER BY timestamp DESC LIMIT ?"
            params = (limit,)

        rows = await self.fetch_all(query, params)

        chat_logs = []
        for row in rows:
            data = dict(row)
            # Parse metadata JSON
            if data["metadata"]:
                import json

                data["metadata"] = json.loads(data["metadata"])
            chat_logs.append(ChatLog(**data))

        return chat_logs

    async def get_chat_log(self, log_id: int) -> Optional[ChatLog]:
        """Get single chat log by ID"""
        query = "SELECT * FROM chat_logs WHERE id = ?"
        row = await self.fetch_one(query, (log_id,))

        if row:
            data = dict(row)
            if data["metadata"]:
                import json

                data["metadata"] = json.loads(data["metadata"])
            return ChatLog(**data)
        return None

    async def get_recent_context(
        self, character_id: int, limit: int = 10
    ) -> List[ChatLog]:
        """Get recent chat history for context"""
        query = """
        SELECT * FROM chat_logs
        WHERE character_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """
        rows = await self.fetch_all(query, (character_id, limit))

        # Return in chronological order (oldest first) for context
        chat_logs = []
        for row in reversed(rows):
            data = dict(row)
            if data["metadata"]:
                import json

                data["metadata"] = json.loads(data["metadata"])
            chat_logs.append(ChatLog(**data))

        return chat_logs

    async def delete_chat_logs(
        self, character_id: int, before_date: Optional[datetime] = None
    ) -> int:
        """Delete chat logs for a character, optionally before a certain date"""
        if before_date:
            query = "DELETE FROM chat_logs WHERE character_id = ? AND timestamp < ?"
            params = (character_id, before_date)
        else:
            query = "DELETE FROM chat_logs WHERE character_id = ?"
            params = (character_id,)

        async with self.get_connection() as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.rowcount

"""
Base Data Access Object

Common functionality for database operations.
"""

import logging
from typing import Optional, Any, AsyncGenerator
from contextlib import asynccontextmanager

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

logger = logging.getLogger(__name__)


class BaseDAO:
    """Base class for Data Access Objects with common database functionality"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        if not aiosqlite:
            raise ImportError("aiosqlite is required for DAO operations")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get database connection with automatic cleanup"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row  # Enable dict-like access
                yield db
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    async def execute_query(self, query: str, params: tuple = ()) -> Optional[Any]:
        """Execute a query and return the result"""
        async with self.get_connection() as db:
            try:
                async with db.execute(query, params) as cursor:
                    return await cursor.fetchone()
            except Exception as e:
                logger.error(f"Query execution failed: {query}, {params}, error: {e}")
                raise
    
    async def execute_many(self, query: str, params_list: list) -> int:
        """Execute query with multiple parameter sets"""
        async with self.get_connection() as db:
            try:
                await db.executemany(query, params_list)
                await db.commit()
                return len(params_list)
            except Exception as e:
                logger.error(f"Batch execution failed: {query}, error: {e}")
                raise
    
    async def fetch_all(self, query: str, params: tuple = ()) -> list:
        """Fetch all results from query"""
        async with self.get_connection() as db:
            try:
                async with db.execute(query, params) as cursor:
                    return await cursor.fetchall()
            except Exception as e:
                logger.error(f"Fetch all failed: {query}, {params}, error: {e}")
                raise
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Any]:
        """Fetch single result from query"""
        async with self.get_connection() as db:
            try:
                async with db.execute(query, params) as cursor:
                    return await cursor.fetchone()
            except Exception as e:
                logger.error(f"Fetch one failed: {query}, {params}, error: {e}")
                raise
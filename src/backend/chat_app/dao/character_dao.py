"""
Character Data Access Object

Handles database operations for character management.
"""

from typing import Optional, List
from datetime import datetime
from .base_dao import BaseDAO
from ..models.schemas import Character


class CharacterDAO(BaseDAO):
    """DAO for character CRUD operations"""
    
    async def create_character(self, name: str, profile: str, personality: str, 
                             avatar_url: Optional[str] = None) -> Character:
        """Create a new character"""
        query = """
        INSERT INTO characters (name, profile, personality, avatar_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        now = datetime.now()
        params = (name, profile, personality, avatar_url, now, now)
        
        async with self.get_connection() as db:
            cursor = await db.execute(query, params)
            await db.commit()
            character_id = cursor.lastrowid
        
        return Character(
            id=character_id,
            name=name,
            profile=profile,
            personality=personality,
            avatar_url=avatar_url,
            created_at=now,
            updated_at=now
        )
    
    async def get_character(self, character_id: int) -> Optional[Character]:
        """Get character by ID"""
        query = "SELECT * FROM characters WHERE id = ?"
        row = await self.fetch_one(query, (character_id,))
        
        if row:
            return Character(**dict(row))
        return None
    
    async def get_character_by_name(self, name: str) -> Optional[Character]:
        """Get character by name"""
        query = "SELECT * FROM characters WHERE name = ?"
        row = await self.fetch_one(query, (name,))
        
        if row:
            return Character(**dict(row))
        return None
    
    async def list_characters(self) -> List[Character]:
        """Get all characters"""
        query = "SELECT * FROM characters ORDER BY created_at DESC"
        rows = await self.fetch_all(query)
        
        return [Character(**dict(row)) for row in rows]
    
    async def update_character(self, character_id: int, **updates) -> Optional[Character]:
        """Update character fields"""
        if not updates:
            return await self.get_character(character_id)
        
        # Build dynamic update query
        set_clauses = []
        params = []
        for field, value in updates.items():
            if field in ['name', 'profile', 'personality', 'avatar_url']:
                set_clauses.append(f"{field} = ?")
                params.append(value)
        
        if not set_clauses:
            return await self.get_character(character_id)
        
        set_clauses.append("updated_at = ?")
        params.append(datetime.now())
        params.append(character_id)
        
        query = f"UPDATE characters SET {', '.join(set_clauses)} WHERE id = ?"
        
        async with self.get_connection() as db:
            await db.execute(query, tuple(params))
            await db.commit()
        
        return await self.get_character(character_id)
    
    async def delete_character(self, character_id: int) -> bool:
        """Delete character"""
        query = "DELETE FROM characters WHERE id = ?"
        
        async with self.get_connection() as db:
            cursor = await db.execute(query, (character_id,))
            await db.commit()
            return cursor.rowcount > 0
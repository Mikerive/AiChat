#!/usr/bin/env python3
"""Debug database operations"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aichat.core.database import list_characters, get_character_by_name, create_character

async def test_basic_db_operations():
    """Test basic database operations"""
    print("=== TESTING BASIC DATABASE OPERATIONS ===")
    
    try:
        # Try to list all characters
        print("Listing all characters...")
        characters = await list_characters()
        print(f"Found {len(characters)} characters:")
        
        for char in characters:
            print(f"  - {char.name} (ID: {char.id})")
        
        # Try to get a specific character
        if characters:
            first_char = characters[0]
            print(f"\nTrying to get character by name: {first_char.name}")
            retrieved = await get_character_by_name(first_char.name)
            
            if retrieved:
                print(f"SUCCESS: Retrieved character {retrieved.name}")
            else:
                print("ERROR: Character not found by name")
        
        # Try to create a new character
        print("\nCreating a new test character...")
        new_char_id = await create_character(
            name="debug_test_character",
            profile="Debug test character",
            personality="test"
        )
        print(f"Created character with ID: {new_char_id}")
        
        # Verify it can be retrieved
        retrieved = await get_character_by_name("debug_test_character")
        if retrieved:
            print(f"SUCCESS: Can retrieve newly created character")
        else:
            print("ERROR: Cannot retrieve newly created character")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_basic_db_operations())
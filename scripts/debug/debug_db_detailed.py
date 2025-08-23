#!/usr/bin/env python3
"""Debug database operations in detail"""

import asyncio
import os
from tests.database.test_db_initializer import setup_test_database, get_test_character_from_db
from aichat.core.database import db_ops

async def debug_database_operations():
    """Debug database operations step by step"""
    print("=== DEBUGGING DATABASE OPERATIONS ===")
    
    try:
        # First check what database file is being used
        from aichat.core.database import DatabaseManager
        db_manager = DatabaseManager()
        print(f"Database file path: {db_manager.db_path}")
        
        # Check if file exists
        db_path = db_manager.db_path
        if os.path.exists(db_path):
            print(f"Database file exists, size: {os.path.getsize(db_path)} bytes")
        else:
            print("Database file does not exist")
        
        print("\n--- BEFORE INITIALIZATION ---")
        
        # Try to list existing characters first
        try:
            existing_chars = await db_ops.list_characters()
            print(f"Existing characters: {len(existing_chars)}")
            for char in existing_chars:
                print(f"  - {char.name} (ID: {char.id})")
        except Exception as e:
            print(f"Error listing existing characters: {e}")
        
        print("\n--- RUNNING INITIALIZATION ---")
        
        # Initialize test database
        success = await setup_test_database(reset=True)
        print(f"Database initialization success: {success}")
        
        print("\n--- AFTER INITIALIZATION ---")
        
        # List characters after initialization
        try:
            chars_after = await db_ops.list_characters()
            print(f"Characters after initialization: {len(chars_after)}")
            for char in chars_after:
                print(f"  - {char.name} (ID: {char.id}) - {char.profile[:50]}...")
        except Exception as e:
            print(f"Error listing characters after init: {e}")
            
        print("\n--- TESTING CHARACTER RETRIEVAL ---")
        
        # Test getting specific characters
        test_names = ["test_character", "hatsune_miku", "ai_assistant"]
        
        for name in test_names:
            print(f"\nTrying to get character: {name}")
            try:
                char = await db_ops.get_character_by_name(name)
                if char:
                    print(f"  SUCCESS: Found {char.name} (ID: {char.id})")
                else:
                    print(f"  NOT FOUND: Character '{name}' not in database")
            except Exception as e:
                print(f"  ERROR: {e}")
        
        print("\n--- TESTING HELPER FUNCTION ---")
        
        # Test the helper function used by fixtures
        for name in test_names:
            print(f"\nTrying get_test_character_from_db: {name}")
            try:
                char = await get_test_character_from_db(name)
                if char:
                    print(f"  SUCCESS: Found {char.name} via helper")
                else:
                    print(f"  NOT FOUND: Character '{name}' via helper")
            except Exception as e:
                print(f"  ERROR: {e}")
                
        return True
        
    except Exception as e:
        print(f"MAJOR ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_database_operations())
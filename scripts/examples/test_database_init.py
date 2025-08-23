#!/usr/bin/env python3
"""
Test the database initialization system
"""

import asyncio
from tests.database.test_db_initializer import setup_test_database, get_test_character_from_db

async def test_database_initialization():
    """Test that the database initialization system works"""
    print("=== TESTING DATABASE INITIALIZATION ===")
    
    try:
        # Initialize test database
        print("Initializing test database...")
        success = await setup_test_database(reset=True)
        
        if not success:
            print("ERROR: Database initialization failed")
            return False
        
        print("SUCCESS: Database initialization successful")
        
        # Test getting test character
        print("Getting test character...")
        test_char = await get_test_character_from_db("test_character")
        
        if not test_char:
            print("ERROR: Test character not found")
            return False
        
        print(f"SUCCESS: Test character found: {test_char.name} (ID: {test_char.id})")
        print(f"   Profile: {test_char.profile}")
        print(f"   Personality: {test_char.personality}")
        
        # Test getting Hatsune Miku character
        print("Getting Hatsune Miku character...")
        miku_char = await get_test_character_from_db("hatsune_miku")
        
        if not miku_char:
            print("ERROR: Hatsune Miku character not found")
            return False
        
        print(f"SUCCESS: Hatsune Miku character found: {miku_char.name} (ID: {miku_char.id})")
        
        print("\nSUCCESS: DATABASE INITIALIZATION SYSTEM IS WORKING!")
        return True
        
    except Exception as e:
        print(f"ERROR: Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_initialization())
    if success:
        print("\nSUCCESS: All database initialization tests passed!")
    else:
        print("\nERROR: Database initialization tests failed!")
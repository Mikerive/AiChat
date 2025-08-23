#!/usr/bin/env python3
"""Simple database test to isolate the character issue"""

import asyncio
from aichat.core.database import db_ops

async def test_simple_character_ops():
    """Test simple character creation and retrieval"""
    print("=== SIMPLE CHARACTER TEST ===")
    
    try:
        # Test 1: List all characters first
        print("\n1. Listing all characters...")
        chars_before = await db_ops.list_characters()
        print(f"Characters before: {len(chars_before)}")
        for char in chars_before:
            print(f"  - {char.name} (ID: {char.id})")
        
        # Test 2: Try to create a simple test character
        print("\n2. Creating test character...")
        test_char_name = "simple_test_char"
        
        # Check if it exists first
        existing = await db_ops.get_character_by_name(test_char_name)
        if existing:
            print(f"Character {test_char_name} already exists")
        else:
            print(f"Character {test_char_name} doesn't exist, creating...")
            
            # Create the character
            new_char = await db_ops.create_character(
                name=test_char_name,
                profile="Simple test character",
                personality="test"
            )
            print(f"Created character: {new_char.name} (ID: {new_char.id})")
        
        # Test 3: Immediately try to retrieve it
        print("\n3. Retrieving the character immediately...")
        retrieved = await db_ops.get_character_by_name(test_char_name)
        if retrieved:
            print(f"SUCCESS: Retrieved {retrieved.name} (ID: {retrieved.id})")
        else:
            print(f"FAILED: Could not retrieve {test_char_name}")
        
        # Test 4: List all characters again
        print("\n4. Listing all characters after creation...")
        chars_after = await db_ops.list_characters()
        print(f"Characters after: {len(chars_after)}")
        for char in chars_after:
            print(f"  - {char.name} (ID: {char.id})")
        
        # Test 5: Try a different approach - create and retrieve in the same context
        print("\n5. Testing batch creation...")
        batch_chars = [
            ("batch_test_1", "Batch test 1", "test"),
            ("batch_test_2", "Batch test 2", "test"),
        ]
        
        for name, profile, personality in batch_chars:
            existing = await db_ops.get_character_by_name(name)
            if not existing:
                char = await db_ops.create_character(name, profile, personality)
                print(f"Created {char.name}")
                
                # Immediate check
                check = await db_ops.get_character_by_name(name)
                if check:
                    print(f"  ✓ Can retrieve {name}")
                else:
                    print(f"  ✗ Cannot retrieve {name}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_character_ops())
    print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")
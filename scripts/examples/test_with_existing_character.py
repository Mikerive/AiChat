#!/usr/bin/env python3
"""Test using existing character in database"""

import asyncio
from aichat.core.database import db_ops
from fastapi.testclient import TestClient
from aichat.backend.main import create_app

async def test_with_existing_character():
    """Test the API with an existing character"""
    print("=== TESTING WITH EXISTING CHARACTER ===")
    
    try:
        # List existing characters
        characters = await db_ops.list_characters()
        print(f"Available characters: {[char.name for char in characters]}")
        
        if not characters:
            print("No characters found - creating one for testing")
            character = await db_ops.create_character(
                name="api_test_character",
                profile="Character for API testing",
                personality="helpful, friendly"
            )
        else:
            character = characters[0]
        
        print(f"Using character: {character.name} (ID: {character.id})")
        
        # Test the API with this character
        app = create_app()
        client = TestClient(app)
        
        chat_message = {
            "text": "Hello! How are you?",
            "character": character.name
        }
        
        response = client.post("/api/chat/chat", json=chat_message)
        print(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: Chat API is working!")
            print(f"User Input: {data.get('user_input', 'N/A')}")
            print(f"AI Response: {data.get('response', 'N/A')}")
            print(f"Character: {data.get('character', 'N/A')}")
            print(f"Emotion: {data.get('emotion', 'N/A')}")
            return True
        else:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_with_existing_character())
    if success:
        print("\nSUCCESS: API test with existing character passed!")
    else:
        print("\nERROR: API test failed!")
#!/usr/bin/env python3
"""Debug chat endpoint error"""

import asyncio
from fastapi.testclient import TestClient
from aichat.backend.main import create_app
from aichat.core.database import db_ops

async def setup_test_character():
    """Set up a test character in the database"""
    try:
        # Try to create a test character
        character_data = {
            "name": "test_character",
            "profile": "A helpful test character",
            "personality": "friendly and helpful"
        }
        
        character = await db_ops.create_character(**character_data)
        print(f"Created test character: {character}")
        return character
    except Exception as e:
        print(f"Error creating character: {e}")
        
        # Try to get existing character
        existing = await db_ops.get_character_by_name("test_character")
        if existing:
            print(f"Using existing character: {existing}")
            return existing
        
        return None

async def main():
    app = create_app()
    client = TestClient(app)
    
    # Set up test character
    character = await setup_test_character()
    if not character:
        print("Failed to set up test character")
        return

    chat_message = {
        "text": "Hello, how are you?",
        "character": "test_character"
    }

    response = client.post("/api/chat/chat", json=chat_message)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code != 200:
        print("ERROR DETAILS:")
        try:
            error_data = response.json()
            print(f"Error Data: {error_data}")
        except:
            print(f"Raw Response Text: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""Debug the list characters API endpoint error"""

import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

async def debug_list_characters():
    """Debug the list characters endpoint 500 error"""
    print("=== DEBUGGING LIST CHARACTERS API ENDPOINT ==")
    
    try:
        # Create FastAPI app
        print("1. Creating FastAPI app...")
        from aichat.backend.main import create_app
        app = create_app()
        client = TestClient(app)
        print("FastAPI app created successfully")
        
        # Make the API call directly first to see raw error
        print("2. Making direct API call...")
        response = client.get("/api/chat/characters")
        print(f"Direct call - Status: {response.status_code}")
        print(f"Direct call - Content: {response.text}")
        
        # Now try with mocking like the test does
        print("3. Making API call with mocks...")
        
        mock_character = {
            "id": 1,
            "name": "test_character", 
            "profile": "A test character",
            "personality": "friendly and helpful",
            "avatar_url": "https://example.com/avatar.png"
        }
        
        with patch('aichat.backend.routes.chat.db_ops') as mock_db_ops, \
             patch('aichat.backend.routes.chat.get_chat_service') as mock_get_chat_service:
            
            # Set up mocks like the fixed test does
            from unittest.mock import AsyncMock
            mock_chat_service = Mock()
            mock_get_chat_service.return_value = mock_chat_service
            # Create a simple object with the character data instead of Mock
            class SimpleCharacter:
                def __init__(self, **kwargs):
                    for key, value in kwargs.items():
                        setattr(self, key, value)
            
            mock_db_ops.list_characters = AsyncMock(return_value=[SimpleCharacter(**mock_character)])
            
            response = client.get("/api/chat/characters")
            print(f"Mocked call - Status: {response.status_code}")
            print(f"Mocked call - Content: {response.text}")
            
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    print(f"Error JSON: {error_data}")
                except:
                    print("Could not parse error as JSON")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_list_characters())
    print(f"Debug result: {'SUCCESS' if success else 'FAILED'}")
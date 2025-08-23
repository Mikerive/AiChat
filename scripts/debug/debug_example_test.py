#!/usr/bin/env python3
"""Debug the example test with database"""

import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from tests.database.test_db_initializer import setup_test_database
import json

async def debug_example_test():
    """Debug the example test database setup"""
    print("=== DEBUGGING EXAMPLE TEST ==")
    
    try:
        # Step 1: Initialize test database
        print("1. Setting up test database...")
        success = await setup_test_database(reset=True)
        print(f"Database setup success: {success}")
        
        # Step 2: Create FastAPI app
        print("2. Creating FastAPI app...")
        from aichat.backend.main import create_app
        app = create_app()
        client = TestClient(app)
        
        # Step 3: Load test data from JSON file
        print("3. Setting up test data...")
        with open("tests/data/test_data.json", "r") as f:
            test_data = json.load(f)
        
        # Create mock database operations
        mock_db_ops = AsyncMock()
        
        # Mock character lookup
        test_char_data = next(c for c in test_data["characters"] if c["name"] == "test_character")
        mock_character = AsyncMock()
        mock_character.name = test_char_data["name"]
        mock_character.id = test_char_data["id"]
        mock_character.profile = test_char_data["profile"]
        mock_character.personality = test_char_data["personality"]
        mock_character.avatar_url = test_char_data.get("avatar_url")
        
        mock_db_ops.get_character_by_name.return_value = mock_character
        
        # Create mock chat service
        mock_chat_service = AsyncMock()
        
        # Create ChatResponse object like we fixed in debug_api_error.py
        from aichat.models.schemas import ChatResponse
        mock_response = ChatResponse(
            user_input="Hello!",
            response="Hello! How can I help you today?",
            character="test_character", 
            emotion="friendly",
            model_used="gpt-4o-mini"
        )
        
        mock_chat_service.process_message.return_value = mock_response
        
        print("4. Making API call...")
        
        # Test the API call with proper mocking
        with patch('aichat.backend.routes.chat.db_ops', mock_db_ops), \
             patch('aichat.backend.routes.chat.get_chat_service') as mock_get_service, \
             patch('aichat.backend.routes.chat.emit_chat_response', return_value=None):
            
            mock_get_service.return_value = mock_chat_service
            
            response = client.post("/api/chat/chat", json={
                "text": "Hello!",
                "character": "test_character"
            })
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response content: {response.text[:500]}")
            
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
    success = asyncio.run(debug_example_test())
    print(f"Debug result: {'SUCCESS' if success else 'FAILED'}")
#!/usr/bin/env python3
"""Debug the API endpoint error"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from aichat.backend.main import create_app

async def debug_api_error():
    """Debug the API endpoint 500 error"""
    print("=== DEBUGGING API ENDPOINT ERROR ===")
    
    try:        
        # Create FastAPI app
        print("1. Creating FastAPI app...")
        app = create_app()
        client = TestClient(app)
        print("FastAPI app created successfully")
        
        # Test basic endpoints
        print("2. Testing health endpoint...")
        response = client.get("/health")
        print(f"Health status: {response.status_code}")
        if response.status_code == 200:
            print(f"Health response: {response.json()}")
        
        print("3. Testing character list endpoint...")
        response = client.get("/api/chat/characters")
        print(f"Characters status: {response.status_code}")
        if response.status_code == 200:
            chars = response.json()
            print(f"Found {len(chars)} characters")
        else:
            print(f"Error response: {response.text}")
        
        print("4. Testing chat endpoint...")
        response = client.post("/api/chat/chat", json={
            "text": "Hello!",
            "character": "test_character"
        })
        
        print(f"Chat response status: {response.status_code}")
        print(f"Chat response content: {response.text}")
        
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"Error JSON: {error_data}")
            except:
                print("Could not parse error as JSON")
                
        return response.status_code == 200
        
    except Exception as e:
        print(f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_api_error())
    print(f"Debug result: {'SUCCESS' if success else 'FAILED'}")
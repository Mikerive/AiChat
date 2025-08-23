#!/usr/bin/env python3
"""Test chat functionality with GPT-4o-mini"""

import asyncio
import traceback
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aichat.backend.services.chat.chat_service import ChatService

async def test_chat_with_gpt4mini():
    """Test chat service with GPT-4o-mini"""
    chat_service = None
    try:
        print("=== TESTING CHAT WITH GPT-4O-MINI ===")
        chat_service = ChatService()
        
        # Try to process a simple message
        response = await chat_service.process_message(
            message="Hello! How are you today?", 
            character_id=1, 
            character_name="hatsune_miku"
        )
        
        print("SUCCESS! Chat is working!")
        print(f"User Input: {response.user_input}")
        
        # Handle potential unicode characters in response
        try:
            print(f"AI Response: {response.response}")
        except UnicodeEncodeError:
            # Convert unicode characters to safe representation
            safe_response = response.response.encode('ascii', 'ignore').decode('ascii')
            print(f"AI Response: {safe_response} [Note: Some unicode characters removed]")
        
        print(f"Character: {response.character}")
        print(f"Emotion: {response.emotion}")
        print(f"Model Used: {response.model_used}")
        
        return True
        
    except Exception as e:
        print("ERROR:", str(e))
        print("FULL TRACEBACK:")
        traceback.print_exc()
        return False
    finally:
        # Clean up resources
        if chat_service and hasattr(chat_service, '_openrouter_service') and chat_service._openrouter_service:
            await chat_service._openrouter_service.close()

if __name__ == "__main__":
    success = asyncio.run(test_chat_with_gpt4mini())
    if success:
        print("\nCHAT SYSTEM IS FULLY OPERATIONAL!")
    else:
        print("\nChat system needs more fixes.")
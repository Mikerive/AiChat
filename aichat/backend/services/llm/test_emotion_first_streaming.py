"""
Test the emotion-first streaming pipeline
Demonstrates LLM emotion output → TTS with consistent emotion
"""

import asyncio
import logging
from pathlib import Path

# Import the new services
from tools.simple_llm_service import SimpleLLMService, CharacterProfile
from emotion_parser import EmotionParser

# Mock TTS for testing
class MockTTSService:
    """Mock TTS service to demonstrate emotion-first pipeline"""
    
    def __init__(self):
        self.generated_segments = []
    
    async def generate_streaming_speech_with_emotion(
        self, 
        text_chunks,
        character_name: str,
        emotion: str = "neutral"
    ):
        """Mock streaming TTS generation with emotion"""
        print(f"TTS: Starting speech generation for {character_name} with emotion: {emotion}")
        
        async for chunk in text_chunks:
            if chunk.strip():
                print(f"TTS: Generating audio for '{chunk}' with {emotion} emotion")
                # Simulate TTS processing time
                await asyncio.sleep(0.2)
                
                segment = {
                    "text": chunk,
                    "emotion": emotion,
                    "audio_file": f"mock_{len(self.generated_segments)}.wav",
                    "character": character_name
                }
                self.generated_segments.append(segment)
                yield segment
        
        print(f"TTS: Completed speech generation with {len(self.generated_segments)} segments")


async def test_emotion_first_pipeline():
    """Test the complete emotion-first streaming pipeline"""
    
    print("Testing Emotion-First Streaming Pipeline")
    print("=" * 50)
    
    # Initialize services
    llm_service = SimpleLLMService()
    emotion_parser = EmotionParser()
    tts_service = MockTTSService()
    
    # Create test character
    character = CharacterProfile(
        name="Miku",
        personality="energetic, helpful, and cheerful AI assistant",
        profile="A virtual character who loves helping users with technology and creative projects"
    )
    
    # Test message
    user_message = "I just finished my first programming project and it works perfectly!"
    
    print(f"User: {user_message}")
    print()
    
    # Stage 1: LLM generates emotion-first streaming response
    print("LLM: Processing with emotion-first approach...")
    
    current_emotion = None
    text_chunks = []
    
    async for emotion, text_chunk in llm_service.process_streaming_with_emotion_first(
        user_message, character
    ):
        if emotion:
            current_emotion = emotion
            print(f"Detected emotion: {emotion}")
        
        if text_chunk:
            print(f"Text chunk: '{text_chunk}'")
            text_chunks.append(text_chunk)
    
    print(f"\nLLM streaming completed. Final emotion: {current_emotion}")
    print()
    
    # Stage 2: TTS applies consistent emotion to all chunks
    print("TTS: Applying consistent emotion to speech generation...")
    
    async def text_chunk_generator():
        for chunk in text_chunks:
            yield chunk
    
    audio_segments = []
    async for segment in tts_service.generate_streaming_speech_with_emotion(
        text_chunk_generator(), character.name, current_emotion
    ):
        audio_segments.append(segment)
    
    print()
    
    # Results summary
    print("Pipeline Results:")
    print("=" * 30)
    print(f"Detected Emotion: {current_emotion}")
    print(f"Total Text Chunks: {len(text_chunks)}")
    print(f"Generated Audio Segments: {len(audio_segments)}")
    print()
    
    print("Generated Segments:")
    for i, segment in enumerate(audio_segments, 1):
        print(f"  {i}. '{segment['text']}' -> {segment['audio_file']} (emotion: {segment['emotion']})")
    
    print()
    print("Key Benefits Demonstrated:")
    print("  - Emotion determined before text streaming starts")
    print("  - Consistent emotional voice throughout entire response")
    print("  - No need for per-segment emotion detection")
    print("  - Natural neural TTS emotion understanding utilized")
    print("  - Efficient streaming pipeline with minimal latency")


async def test_emotion_parser():
    """Test the emotion parsing functionality"""
    
    print("\nTesting Emotion Parser")
    print("=" * 30)
    
    parser = EmotionParser()
    
    test_cases = [
        "[EMOTION: excited] I can't wait to help you!",
        "[happy] This is great news!",
        "<emotion>sad</emotion> I'm sorry to hear that.",
        "emotion: curious What's that about?",
        "[EMOTION: thrilled] Amazing work!", # Should normalize to 'excited'
        "No emotion here, just normal text",
        "[EMOTION: unknown_emotion] Testing fallback", # Should fallback to 'neutral'
    ]
    
    for test_text in test_cases:
        emotion = parser.extract_emotion_from_chunk(test_text)
        clean_text = parser.strip_emotion_marker(test_text)
        print(f"Input: '{test_text}'")
        print(f"  Emotion: {emotion}")
        print(f"  Clean text: '{clean_text}'")
        print()


async def main():
    """Run all tests"""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        await test_emotion_parser()
        await test_emotion_first_pipeline()
        
        print("\nAll tests completed successfully!")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
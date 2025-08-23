"""
Test the intensity-first streaming pipeline with Chatterbox TTS
Demonstrates LLM intensity output -> Chatterbox TTS with exaggeration control
"""

import asyncio
import logging
from pathlib import Path

# Import the new services
from tools.simple_llm_service import SimpleLLMService, CharacterProfile
from emotion_parser import IntensityParser

# Mock Chatterbox TTS for testing
class MockChatterboxTTS:
    """Mock Chatterbox TTS service to demonstrate intensity-first pipeline"""
    
    def __init__(self):
        self.generated_segments = []
    
    async def generate_streaming_speech_with_intensity(
        self, 
        text_chunks,
        character_name: str,
        exaggeration: float = 0.7
    ):
        """Mock streaming TTS generation with Chatterbox exaggeration"""
        intensity_desc = self._get_intensity_description(exaggeration)
        print(f"TTS: Starting Chatterbox speech for {character_name} with exaggeration: {exaggeration:.2f} ({intensity_desc})")
        
        async for chunk in text_chunks:
            if chunk.strip():
                print(f"TTS: Generating audio for '{chunk}' with {exaggeration:.2f} exaggeration")
                # Simulate TTS processing time
                await asyncio.sleep(0.15)
                
                segment = {
                    "text": chunk,
                    "exaggeration": exaggeration,
                    "intensity_desc": intensity_desc,
                    "audio_file": f"chatterbox_{len(self.generated_segments)}.wav",
                    "character": character_name,
                    "model": "chatterbox"
                }
                self.generated_segments.append(segment)
                yield segment
        
        print(f"TTS: Completed Chatterbox generation with {len(self.generated_segments)} segments")
    
    def _get_intensity_description(self, exaggeration: float) -> str:
        """Get human-readable description of exaggeration level"""
        if exaggeration <= 0.2:
            return "monotone/robotic"
        elif exaggeration <= 0.4:
            return "subdued/quiet"
        elif exaggeration <= 0.6:
            return "minimal/natural"
        elif exaggeration <= 0.8:
            return "normal/balanced"
        elif exaggeration <= 1.0:
            return "moderate/expressive"
        elif exaggeration <= 1.3:
            return "high/energetic"
        elif exaggeration <= 1.6:
            return "dramatic/intense"
        elif exaggeration <= 1.9:
            return "extreme/theatrical"
        else:
            return "maximum/over-the-top"


async def test_intensity_first_pipeline():
    """Test the complete intensity-first streaming pipeline with Chatterbox"""
    
    print("Testing Intensity-First Streaming Pipeline (Chatterbox TTS)")
    print("=" * 60)
    
    # Initialize services
    llm_service = SimpleLLMService()
    intensity_parser = IntensityParser()
    tts_service = MockChatterboxTTS()
    
    # Create test character
    character = CharacterProfile(
        name="Miku",
        personality="energetic, helpful, and cheerful AI assistant",
        profile="A virtual character who loves helping users with technology and creative projects"
    )
    
    # Test message
    user_message = "I just built my first AI chatbot and it's working amazingly well!"
    
    print(f"User: {user_message}")
    print()
    
    # Stage 1: LLM generates intensity-first streaming response
    print("LLM: Processing with intensity-first approach...")
    
    current_exaggeration = None
    text_chunks = []
    
    async for exaggeration, text_chunk in llm_service.process_streaming_with_intensity_first(
        user_message, character
    ):
        if exaggeration is not None:
            current_exaggeration = exaggeration
            intensity_desc = tts_service._get_intensity_description(exaggeration)
            print(f"Detected intensity: {exaggeration:.2f} ({intensity_desc})")
        
        if text_chunk:
            print(f"Text chunk: '{text_chunk}'")
            text_chunks.append(text_chunk)
    
    print(f"\nLLM streaming completed. Final exaggeration: {current_exaggeration:.2f}")
    print()
    
    # Stage 2: Chatterbox TTS applies consistent exaggeration to all chunks
    print("Chatterbox TTS: Applying consistent exaggeration to speech generation...")
    
    async def text_chunk_generator():
        for chunk in text_chunks:
            yield chunk
    
    audio_segments = []
    async for segment in tts_service.generate_streaming_speech_with_intensity(
        text_chunk_generator(), character.name, current_exaggeration
    ):
        audio_segments.append(segment)
    
    print()
    
    # Results summary
    print("Pipeline Results:")
    print("=" * 30)
    print(f"Detected Intensity: {current_exaggeration:.2f}")
    print(f"Intensity Description: {audio_segments[0]['intensity_desc'] if audio_segments else 'N/A'}")
    print(f"Total Text Chunks: {len(text_chunks)}")
    print(f"Generated Audio Segments: {len(audio_segments)}")
    print()
    
    print("Generated Segments:")
    for i, segment in enumerate(audio_segments, 1):
        print(f"  {i}. '{segment['text']}' -> {segment['audio_file']} (exaggeration: {segment['exaggeration']:.2f})")
    
    print()
    print("Key Benefits Demonstrated:")
    print("  - Intensity determined before text streaming starts")
    print("  - Consistent Chatterbox exaggeration throughout entire response")
    print("  - Maps to actual TTS model capabilities (0.0-2.0)")
    print("  - No complex emotion mapping required")
    print("  - Efficient streaming pipeline with Chatterbox-native parameters")


async def test_intensity_parser():
    """Test the intensity parsing functionality"""
    
    print("\nTesting Intensity Parser")
    print("=" * 30)
    
    parser = IntensityParser()
    
    test_cases = [
        "[INTENSITY: high] I'm so excited to help!",
        "[dramatic] This is incredible news!",
        "<intensity>low</intensity> I'm feeling a bit tired today.",
        "intensity: normal What can I do for you?",
        "[INTENSITY: theatrical] AMAZING work on this project!",
        "[INTENSITY: 1.5] Custom numeric intensity level",
        "No intensity here, just normal text",
        "[INTENSITY: unknown_level] Testing fallback",
        "[INTENSITY: extreme] Maximum expressiveness!",
        "[flat] Very monotone response.",
    ]
    
    print("Input -> Parsed Intensity -> Exaggeration Value")
    print("-" * 50)
    
    for test_text in test_cases:
        intensity_value = parser.extract_intensity_from_chunk(test_text)
        clean_text = parser.strip_intensity_marker(test_text)
        
        if intensity_value is not None:
            intensity_desc = MockChatterboxTTS()._get_intensity_description(intensity_value)
            print(f"'{test_text}'")
            print(f"  Intensity: {intensity_value:.2f} ({intensity_desc})")
            print(f"  Clean text: '{clean_text}'")
        else:
            print(f"'{test_text}'")
            print(f"  Intensity: None (no marker detected)")
            print(f"  Clean text: '{clean_text}'")
        print()


async def demonstrate_chatterbox_exaggeration_levels():
    """Demonstrate different Chatterbox exaggeration levels"""
    
    print("\nChatterbox Exaggeration Level Examples")
    print("=" * 40)
    
    sample_text = "Hello, I'm excited to help you today!"
    exaggeration_examples = [
        (0.0, "flat"),
        (0.3, "low"), 
        (0.5, "neutral"),
        (0.7, "normal"),
        (1.0, "moderate"),
        (1.2, "high"),
        (1.5, "dramatic"),
        (1.8, "extreme"),
        (2.0, "theatrical")
    ]
    
    tts = MockChatterboxTTS()
    
    print("Sample text: \"Hello, I'm excited to help you today!\"")
    print()
    print("Exaggeration | Level      | Description")
    print("-" * 45)
    
    for exaggeration, level in exaggeration_examples:
        desc = tts._get_intensity_description(exaggeration)
        print(f"{exaggeration:10.1f} | {level:10s} | {desc}")


async def main():
    """Run all tests"""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        await test_intensity_parser()
        await demonstrate_chatterbox_exaggeration_levels()
        await test_intensity_first_pipeline()
        
        print("\nAll intensity streaming tests completed successfully!")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
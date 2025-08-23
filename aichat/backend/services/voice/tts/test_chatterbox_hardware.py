"""
Test Chatterbox TTS hardware detection and GPU fallback to CPU
Verifies device detection, hardware information, and service initialization
"""

import asyncio
import logging
from pathlib import Path

# Import the Chatterbox TTS service
from chatterbox_tts_service import ChatterboxTTSService

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_hardware_detection():
    """Test hardware detection and device information"""
    
    print("Chatterbox TTS Hardware Detection Test")
    print("=" * 50)
    
    # Initialize service
    tts_service = ChatterboxTTSService()
    
    print(f"Detected device: {tts_service.device}")
    print(f"CPU fallback mode: {tts_service.cpu_fallback}")
    print()
    
    # Get detailed device information
    device_info = tts_service.get_device_info()
    
    print("Device Information:")
    print("-" * 30)
    for key, value in device_info.items():
        print(f"  {key}: {value}")
    print()
    
    # Test service initialization
    print("Testing service initialization...")
    success = await tts_service.initialize()
    
    if success:
        print("✓ Service initialized successfully")
        
        # Get service status
        status = await tts_service.get_service_status()
        
        print(f"Service status: {status['status']}")
        print(f"Performance mode: {status['performance_mode']}")
        print(f"Model loaded: {status['model_loaded']}")
        
    else:
        print("✗ Service initialization failed")
    
    print()


async def test_speech_generation():
    """Test speech generation with hardware detection"""
    
    print("Testing Speech Generation")
    print("-" * 30)
    
    tts_service = ChatterboxTTSService()
    
    # Initialize service
    if not await tts_service.initialize():
        print("Failed to initialize TTS service")
        return
    
    test_text = "Hello, this is a test of Chatterbox TTS with hardware detection."
    character_name = "TestCharacter"
    
    # Test different exaggeration levels
    exaggeration_levels = [0.0, 0.7, 1.2, 2.0]
    
    for exaggeration in exaggeration_levels:
        print(f"Generating speech with exaggeration {exaggeration:.1f}...")
        
        audio_path = await tts_service.generate_speech_segment(
            text=test_text,
            character_name=character_name,
            exaggeration=exaggeration
        )
        
        if audio_path:
            device_mode = "GPU-accelerated" if not tts_service.cpu_fallback else "CPU-optimized"
            print(f"  ✓ Generated: {audio_path.name} ({device_mode})")
        else:
            print(f"  ✗ Failed to generate audio")
    
    print()


async def test_streaming_speech():
    """Test streaming speech generation with punctuation-based segmentation"""
    
    print("Testing Streaming Speech Generation")
    print("-" * 40)
    
    tts_service = ChatterboxTTSService()
    
    if not await tts_service.initialize():
        print("Failed to initialize TTS service")
        return
    
    test_text = "Hello there! How are you today? I'm excited to help you with your project. Let's get started, shall we?"
    character_name = "StreamingTest"
    exaggeration = 1.0
    
    print(f"Input text: \"{test_text}\"")
    print(f"Exaggeration level: {exaggeration}")
    print()
    
    # Generate streaming segments
    segments = await tts_service.generate_streaming_speech(
        text=test_text,
        character_name=character_name,
        exaggeration=exaggeration
    )
    
    print("Generated streaming segments:")
    for i, segment in enumerate(segments, 1):
        punctuation = segment.get('punctuation', 'None')
        pause_duration = segment.get('pause_duration', 0.0)
        audio_file = segment.get('audio_file', 'N/A')
        
        print(f"  {i}. \"{segment['text']}\"")
        print(f"     Punctuation: {punctuation}, Pause: {pause_duration}s")
        print(f"     Audio: {Path(audio_file).name if audio_file != 'N/A' else 'N/A'}")
        print()
    
    device_mode = "GPU-accelerated" if not tts_service.cpu_fallback else "CPU-optimized"
    print(f"Generated {len(segments)} segments using {device_mode} processing")


async def test_device_scenarios():
    """Test different device scenarios"""
    
    print("Testing Device Scenarios")
    print("-" * 30)
    
    # Test 1: Normal initialization
    print("1. Normal device detection:")
    tts1 = ChatterboxTTSService()
    device_info1 = tts1.get_device_info()
    print(f"   Device: {device_info1['device']}")
    print(f"   PyTorch available: {device_info1['pytorch_available']}")
    print(f"   CUDA available: {device_info1['cuda_available']}")
    
    if device_info1['cuda_available']:
        print(f"   GPU: {device_info1['gpu_name']}")
        print(f"   VRAM: {device_info1['vram_gb']:.1f} GB")
        if device_info1['vram_gb'] >= 6.0:
            print("   ✓ Sufficient VRAM for GPU acceleration")
        else:
            print("   ⚠ Insufficient VRAM, will use CPU fallback")
    else:
        print("   No CUDA GPU detected, using CPU")
    
    print()
    
    # Test 2: Service status comparison
    await tts1.initialize()
    status = await tts1.get_service_status()
    
    print("2. Service status information:")
    print(f"   Performance mode: {status['performance_mode']}")
    print(f"   CPU fallback: {status['cpu_fallback']}")
    print(f"   Model loaded: {status['model_loaded']}")
    print()


async def main():
    """Run all hardware detection tests"""
    
    try:
        await test_hardware_detection()
        await test_device_scenarios()
        await test_speech_generation()
        await test_streaming_speech()
        
        print("All hardware detection tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
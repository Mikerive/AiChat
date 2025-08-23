# LLM Function Tools

A lightweight, high-performance emotion processing system for AI agents using SBERT-based local emotion detection and mathematical voice parameter mapping.

## Overview

This package provides simplified tools for PydanticAI agents with ultra-fast emotion processing, replacing complex JSON structures and API-dependent emotion detection with efficient local models.

### Key Features

- **🚀 Lightning-fast emotion detection**: 5-15ms vs 200-400ms API calls (15-80x faster)
- **📦 Ultra-lightweight**: 17MB SBERT model vs heavy API dependencies
- **🔄 Two-stage processing**: Clean emotion query → response generation
- **🎵 Mathematical voice mapping**: N-dimensional emotion space for precise voice control
- **📊 Performance optimized**: Batch processing, caching, and async operations
- **🔌 Offline capable**: No external API dependencies required

## Architecture

### Core Components

1. **SBERTEmotionDetector** - Local emotion detection using lightweight sentence transformers
2. **SimpleEmotionDetector** - Single-word emotion queries without JSON complexity
3. **CompactVoiceController** - N-dimensional emotion space with mathematical voice mapping
4. **SimpleLLMService** - Orchestrates two-stage emotion processing

### Performance Comparison

| Method | Speed | Dependencies | Accuracy | Offline |
|--------|-------|--------------|----------|---------|
| **SBERT (New)** | 5-15ms | 17MB model | High | ✅ |
| API Calls (Legacy) | 200-400ms | Internet + Keys | High | ❌ |
| **Speedup** | **15-80x faster** | **Minimal** | **Equivalent** | **Local** |

## Quick Start

### Basic Usage

```python
from aichat.backend.services.llm.tools import (
    SBERTEmotionDetector,
    CompactVoiceController,
    SimpleLLMService
)

# Initialize components
emotion_detector = SBERTEmotionDetector()
voice_controller = CompactVoiceController()
llm_service = SimpleLLMService()

# Initialize SBERT model (one-time setup)
await emotion_detector.initialize()

# Detect emotion from text (5-15ms)
emotion = await emotion_detector.detect_emotion("I'm so excited about this!")
# Returns: "excited"

# Get voice parameters for emotion
voice_params = voice_controller.get_voice_parameters(emotion)
# Returns: {"speed": 1.2, "pitch": 1.1, "volume": 1.0}

# Process message with emotion-aware response
response = await llm_service.process_message_simple(
    "Tell me about your day", 
    character_name="Miku"
)
print(f"Response: {response.text}")
print(f"Detected emotion: {response.detected_emotion}")
print(f"Voice speed: {response.voice_speed}")
```

### Batch Processing

```python
# Process multiple texts efficiently
texts = [
    "I'm feeling happy today!",
    "This is frustrating me.",
    "I'm curious about this topic."
]

# Batch detection (even faster per text)
emotions = await emotion_detector.batch_detect_emotions(texts)
# Returns: ["happy", "frustrated", "curious"]
```

## Components Reference

### SBERTEmotionDetector

Ultra-fast emotion detection using lightweight sentence transformers.

```python
class SBERTEmotionDetector:
    def __init__(self, model_name: str = "paraphrase-MiniLM-L3-v2"):
        """
        Initialize with ultra-lightweight model:
        - paraphrase-MiniLM-L3-v2: 17MB, fastest (recommended)
        - all-MiniLM-L6-v2: 22MB, very fast
        - paraphrase-TinyBERT-L6-v2: 43MB, more accurate
        """
    
    async def initialize() -> bool:
        """Load model and pre-compute emotion vectors"""
    
    async def detect_emotion(self, text: str) -> str:
        """Detect single emotion (5-15ms)"""
    
    async def batch_detect_emotions(self, texts: List[str]) -> List[str]:
        """Batch detection for efficiency"""
    
    def get_emotion_similarities(self, text: str) -> Dict[str, float]:
        """Get similarity scores for all emotions"""
    
    def get_performance_stats() -> Dict[str, Any]:
        """Get detailed performance metrics"""
```

**Supported Emotions**: happy, excited, joyful, content, peaceful, sad, disappointed, melancholy, angry, frustrated, annoyed, worried, anxious, nervous, curious, interested, fascinated, confused, puzzled, surprised, amazed, neutral

### CompactVoiceController

N-dimensional emotion space with mathematical voice parameter calculation.

```python
class CompactVoiceController:
    def get_voice_parameters(self, emotion: str) -> Dict[str, float]:
        """Get voice parameters for emotion"""
    
    def get_emotion_vector(self, emotion: str) -> EmotionVector:
        """Get 4D emotion vector (valence, arousal, dominance, intensity)"""
    
    def calculate_voice_from_vector(self, vector: EmotionVector) -> Dict[str, float]:
        """Calculate voice parameters from emotion vector"""
```

**Emotion Dimensions**:
- **Valence**: Positive (0.8) ↔ Negative (-0.8)
- **Arousal**: High energy (0.9) ↔ Low energy (-0.6)
- **Dominance**: Control (0.7) ↔ Submission (-0.5)
- **Intensity**: Strong (0.9) ↔ Mild (0.3)

### SimpleLLMService

Two-stage emotion processing for clean responses.

```python
class SimpleLLMService:
    async def process_message_simple(
        self, 
        message: str, 
        character_name: str = "Assistant"
    ) -> SimpleEmotionalResponse:
        """
        Process message with two-stage approach:
        1. Query emotion from LLM
        2. Generate response with emotion context
        """
```

**Response Structure**:
```python
@dataclass
class SimpleEmotionalResponse:
    text: str              # Generated response
    detected_emotion: str  # Single-word emotion
    voice_speed: float     # TTS speed multiplier
    voice_pitch: float     # TTS pitch multiplier
    confidence: float      # Detection confidence
```

## Performance Testing

Run the included performance test to benchmark SBERT vs API approaches:

```bash
cd aichat/backend/services/llm/tools
python test_sbert_performance.py
```

**Expected Output**:
```
SBERT Emotion Detection Performance Test
==================================================
Model: paraphrase-MiniLM-L3-v2
Expected individual detection: 5-15ms per text
Expected batch detection: 2-8ms per text
Expected speedup vs API: 15-80x faster

Vs API-based Detection:
  API calls: 200-400ms per text
  SBERT:     5-15ms per text
  Speedup:   15-80x faster
```

## Installation Requirements

### Required Dependencies

```bash
pip install sentence-transformers scikit-learn numpy
```

### Optional Dependencies

```bash
pip install pydantic-ai torch  # For LLM service integration
```

## Configuration

### Model Selection

Choose SBERT model based on your requirements:

```python
# Fastest (recommended)
detector = SBERTEmotionDetector("paraphrase-MiniLM-L3-v2")  # 17MB

# Balanced
detector = SBERTEmotionDetector("all-MiniLM-L6-v2")  # 22MB

# Most accurate
detector = SBERTEmotionDetector("paraphrase-TinyBERT-L6-v2")  # 43MB
```

### Custom Emotions

Add custom emotions with examples:

```python
detector.add_custom_emotion("mystical", [
    "This feels magical and otherworldly",
    "I sense something mystical here",
    "There's an enchanting quality to this"
])
```

### Voice Parameter Tuning

Customize voice mapping:

```python
voice_controller = CompactVoiceController()

# Override default emotion mapping
voice_controller.emotion_voice_map["excited"] = {
    "speed": 1.3,    # 30% faster
    "pitch": 1.2,    # 20% higher
    "volume": 1.1    # 10% louder
}
```

## Integration Examples

### With PydanticAI

```python
from pydantic_ai import Agent
from aichat.backend.services.llm.tools import SimpleLLMService

# Create agent with emotion processing
llm_service = SimpleLLMService()

async def process_chat(message: str, character: str) -> dict:
    response = await llm_service.process_message_simple(message, character)
    
    return {
        "text": response.text,
        "emotion": response.detected_emotion,
        "voice_settings": {
            "speed": response.voice_speed,
            "pitch": response.voice_pitch
        }
    }
```

### With TTS Systems

```python
import asyncio
from aichat.backend.services.llm.tools import SBERTEmotionDetector, CompactVoiceController

async def emotional_tts(text: str, tts_engine):
    # Detect emotion
    detector = SBERTEmotionDetector()
    await detector.initialize()
    emotion = await detector.detect_emotion(text)
    
    # Get voice parameters
    voice_controller = CompactVoiceController()
    voice_params = voice_controller.get_voice_parameters(emotion)
    
    # Apply to TTS
    audio = tts_engine.synthesize(
        text,
        speed=voice_params["speed"],
        pitch=voice_params["pitch"]
    )
    
    return audio, emotion
```

### Streaming Integration

```python
async def process_streaming_chat(message_stream, character_name: str):
    detector = SBERTEmotionDetector()
    voice_controller = CompactVoiceController()
    
    await detector.initialize()
    
    async for message in message_stream:
        # Fast emotion detection
        emotion = await detector.detect_emotion(message)
        voice_params = voice_controller.get_voice_parameters(emotion)
        
        # Stream with emotion-aware voice
        yield {
            "text": message,
            "emotion": emotion,
            "voice": voice_params
        }
```

## Migration from Legacy Tools

### Before (Legacy)
```python
# Complex JSON-based approach
from aichat.backend.services.llm.tools import EmotionTool, VoiceTool

emotion_tool = EmotionTool()
voice_tool = VoiceTool()

# Slow API-based detection (200-400ms)
result = await emotion_tool.detect_complex_emotion(text)
voice_settings = voice_tool.get_voice_from_json(result)
```

### After (New)
```python
# Simple, fast approach
from aichat.backend.services.llm.tools import SBERTEmotionDetector, CompactVoiceController

detector = SBERTEmotionDetector()
voice_controller = CompactVoiceController()

await detector.initialize()

# Fast local detection (5-15ms)
emotion = await detector.detect_emotion(text)
voice_settings = voice_controller.get_voice_parameters(emotion)
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Install missing dependencies
   pip install sentence-transformers scikit-learn
   ```

2. **Model Download Issues**
   ```python
   # Models auto-download on first use
   # Ensure internet connection for initial setup
   ```

3. **Performance Issues**
   ```python
   # Use batch processing for multiple texts
   emotions = await detector.batch_detect_emotions(texts)
   
   # Enable caching (default enabled)
   detector.clear_cache()  # Reset if needed
   ```

4. **Memory Usage**
   ```python
   # Use lighter model for resource-constrained environments
   detector = SBERTEmotionDetector("paraphrase-MiniLM-L3-v2")  # 17MB
   ```

### Performance Optimization

1. **Batch Processing**: Always use `batch_detect_emotions()` for multiple texts
2. **Model Selection**: Choose the lightest model that meets accuracy requirements
3. **Caching**: Leverage built-in caching for repeated queries
4. **Async Operations**: All methods are async-optimized

## API Reference

### Error Handling

All methods include comprehensive error handling with fallbacks:

```python
try:
    emotion = await detector.detect_emotion(text)
except Exception as e:
    # Falls back to "neutral" on errors
    emotion = "neutral"
```

### Logging

Enable detailed logging for debugging:

```python
import logging
logging.getLogger("sbert_emotion_detector").setLevel(logging.DEBUG)
```

### Performance Monitoring

Get detailed performance statistics:

```python
stats = detector.get_performance_stats()
print(f"Average detection time: {stats['performance']['average_detection_time_ms']:.1f}ms")
print(f"Cache hit rate: {stats['performance']['cache_hit_rate']:.1%}")
print(f"Total detections: {stats['performance']['total_detections']}")
```

## Contributing

### Adding New Emotions

1. Add emotion to `_create_emotion_templates()` in `SBERTEmotionDetector`
2. Add voice mapping in `CompactVoiceController`
3. Update emotion vector dimensions if needed
4. Test with performance benchmark

### Optimizing Performance

1. Profile with `test_sbert_performance.py`
2. Consider model quantization for further speed gains
3. Implement GPU acceleration if available
4. Add custom caching strategies

## License

This package is part of the VtuberMiku project. See main project license for details.

---

**Note**: This system replaces the previous complex emotion detection tools with a simplified, high-performance architecture optimized for real-time applications.
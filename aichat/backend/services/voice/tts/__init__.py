"""
Text-to-Speech Services Package

Provides multiple TTS backends with smart hardware-based selection:
- ChatterboxTTSService: CPU-optimized TTS using ResembleAI Chatterbox
- OrpheusTTSService: GPU-accelerated TTS using Orpheus-1B
- SmartTTSSelector: Intelligent backend selection based on hardware capabilities
- StreamingTTSIntegration: Real-time TTS with OpenRouter streaming integration
"""

from .chatterbox_tts_service import ChatterboxTTSService

try:
    from .orpheus_tts_service import OrpheusTTSService
    ORPHEUS_AVAILABLE = True
except ImportError:
    OrpheusTTSService = None
    ORPHEUS_AVAILABLE = False

try:
    from .smart_tts_selector import SmartTTSSelector, TTSBackend
    SMART_SELECTOR_AVAILABLE = True  
except ImportError:
    SmartTTSSelector = None
    TTSBackend = None
    SMART_SELECTOR_AVAILABLE = False

try:
    from .streaming_tts_integration import StreamingTTSIntegration, StreamingMode, StreamingConfig
    STREAMING_INTEGRATION_AVAILABLE = True
except ImportError:
    StreamingTTSIntegration = None
    StreamingMode = None
    StreamingConfig = None
    STREAMING_INTEGRATION_AVAILABLE = False

# Build __all__ dynamically based on what's available
__all__ = ["ChatterboxTTSService"]

if ORPHEUS_AVAILABLE:
    __all__.append("OrpheusTTSService")

if SMART_SELECTOR_AVAILABLE:
    __all__.extend(["SmartTTSSelector", "TTSBackend"])

if STREAMING_INTEGRATION_AVAILABLE:
    __all__.extend(["StreamingTTSIntegration", "StreamingMode", "StreamingConfig"])
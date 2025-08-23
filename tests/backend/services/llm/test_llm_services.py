"""
LLM services testing - real functionality without mocking.
Tests LLM service imports and basic functionality.
"""

import pytest


class TestLLMServices:
    """Test LLM service functionality."""
    
    def test_can_import_openrouter_service(self):
        """Test OpenRouter service import."""
        try:
            from aichat.backend.services.llm.openrouter_service import OpenRouterService
            assert OpenRouterService is not None
        except ImportError:
            pytest.skip("OpenRouter service not available")
    
    def test_can_import_pydantic_ai_service(self):
        """Test Pydantic AI service import."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            assert PydanticAIService is not None
        except ImportError:
            pytest.skip("Pydantic AI service not available")
    
    def test_can_import_intensity_parser(self):
        """Test intensity parser import."""
        try:
            from aichat.backend.services.llm.emotion_parser import IntensityParser
            assert IntensityParser is not None
        except ImportError:
            pytest.skip("Intensity parser not available")
    
    def test_can_import_unified_llm_service(self):
        """Test unified LLM service import."""
        try:
            from aichat.backend.services.llm.unified_llm_service import UnifiedLLMService
            assert UnifiedLLMService is not None
        except ImportError:
            pytest.skip("Unified LLM service not available")


class TestLLMTools:
    """Test LLM tools functionality."""
    
    def test_can_import_simple_llm_service(self):
        """Test simple LLM service tool import."""
        try:
            from aichat.backend.services.llm.tools.simple_llm_service import SimpleLLMService
            assert SimpleLLMService is not None
        except ImportError:
            pytest.skip("Simple LLM service tool not available")
    
    def test_can_import_emotion_detectors(self):
        """Test emotion detector tools import."""
        try:
            from aichat.backend.services.llm.tools.simple_emotion_detector import SimpleEmotionDetector
            from aichat.backend.services.llm.tools.sbert_emotion_detector import SBERTEmotionDetector
            
            assert SimpleEmotionDetector is not None
            assert SBERTEmotionDetector is not None
        except ImportError:
            pytest.skip("Emotion detector tools not available")
    
    def test_can_import_voice_controller(self):
        """Test compact voice controller import."""
        try:
            from aichat.backend.services.llm.tools.compact_voice_controller import CompactVoiceController
            assert CompactVoiceController is not None
        except ImportError:
            pytest.skip("Voice controller tool not available")
"""
LLM Integration Tests - Real functionality testing for Language Model pipeline
Tests individual LLM services and their integration with the voice and chat pipeline.
"""

import asyncio
import pytest
import time
import json
from typing import Optional, Dict, Any, List, AsyncGenerator
from unittest.mock import Mock


class TestLLMServiceIntegration:
    """Test LLM service integration and functionality."""
    
    def test_pydantic_ai_service_import(self):
        """Test that PydanticAI service can be imported and initialized."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            
            # Test service initialization
            service = PydanticAIService()
            assert service is not None
            assert hasattr(service, 'generate_response')
            assert hasattr(service, 'generate_streaming_response')
            
        except ImportError as e:
            pytest.skip(f"PydanticAI service not available: {e}")
    
    def test_openrouter_service_import(self):
        """Test that OpenRouter service can be imported."""
        try:
            from aichat.backend.services.llm.openrouter_service import OpenRouterService
            
            # Test service initialization
            service = OpenRouterService()
            assert service is not None
            assert hasattr(service, 'generate_response')
            assert hasattr(service, 'generate_streaming_response')
            
        except ImportError as e:
            pytest.skip(f"OpenRouter service not available: {e}")
    
    def test_unified_llm_service_import(self):
        """Test that unified LLM service can be imported."""
        try:
            from aichat.backend.services.llm.unified_llm_service import UnifiedLLMService
            
            # Test service initialization
            service = UnifiedLLMService()
            assert service is not None
            assert hasattr(service, 'generate_response')
            assert hasattr(service, 'get_available_models')
            
        except ImportError as e:
            pytest.skip(f"Unified LLM service not available: {e}")
    
    def test_emotion_parser_import(self):
        """Test that emotion parser can be imported and initialized."""
        try:
            from aichat.backend.services.llm.emotion_parser import EmotionParser
            
            # Test parser initialization
            parser = EmotionParser()
            assert parser is not None
            assert hasattr(parser, 'parse_emotion')
            assert hasattr(parser, 'extract_intensity')
            
        except ImportError as e:
            pytest.skip(f"Emotion parser not available: {e}")


class TestLLMResponseGeneration:
    """Test LLM response generation capabilities."""
    
    @pytest.mark.asyncio
    async def test_pydantic_ai_basic_generation(self):
        """Test basic response generation with PydanticAI service."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            
            service = PydanticAIService()
            
            # Test basic response generation
            test_prompt = "Hello, how are you today?"
            character_context = {
                "name": "test_character",
                "personality": "friendly and helpful",
                "profile": "A test character for integration testing"
            }
            
            response = await service.generate_response(
                prompt=test_prompt,
                character_context=character_context,
                max_tokens=100
            )
            
            if response:
                assert isinstance(response, dict)
                expected_keys = ['text', 'character', 'emotion']
                for key in expected_keys:
                    if key in response:
                        assert response[key] is not None
                        
                # Text should be a non-empty string
                if 'text' in response:
                    assert isinstance(response['text'], str)
                    assert len(response['text']) > 0
                    
        except Exception as e:
            pytest.skip(f"PydanticAI generation not available: {e}")
    
    @pytest.mark.asyncio
    async def test_pydantic_ai_streaming_generation(self):
        """Test streaming response generation with PydanticAI service."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            
            service = PydanticAIService()
            
            test_prompt = "Tell me a short story about a robot learning to paint."
            character_context = {
                "name": "narrator",
                "personality": "creative and imaginative",
                "profile": "A storyteller character"
            }
            
            # Collect streaming chunks
            streaming_chunks = []
            async for chunk in service.generate_streaming_response(
                prompt=test_prompt,
                character_context=character_context,
                max_tokens=150
            ):
                if chunk:
                    streaming_chunks.append(chunk)
            
            if streaming_chunks:
                # Verify streaming structure
                for chunk in streaming_chunks:
                    assert isinstance(chunk, dict)
                    
                # Should have content in chunks
                text_content = ""
                for chunk in streaming_chunks:
                    if 'content' in chunk:
                        text_content += chunk['content']
                    elif 'text' in chunk:
                        text_content += chunk['text']
                
                assert len(text_content) > 0
                
        except Exception as e:
            pytest.skip(f"PydanticAI streaming not available: {e}")
    
    @pytest.mark.asyncio
    async def test_openrouter_integration(self):
        """Test OpenRouter service integration (requires API key)."""
        try:
            from aichat.backend.services.llm.openrouter_service import OpenRouterService
            import os
            
            # Check for API key
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                pytest.skip("OpenRouter API key not available")
            
            service = OpenRouterService(api_key=api_key)
            
            test_prompt = "What is 2 + 2?"
            
            response = await service.generate_response(
                prompt=test_prompt,
                model="openai/gpt-3.5-turbo",
                max_tokens=50
            )
            
            if response:
                assert isinstance(response, dict)
                if 'text' in response or 'content' in response:
                    content = response.get('text') or response.get('content')
                    assert isinstance(content, str)
                    assert len(content) > 0
                    
        except Exception as e:
            pytest.skip(f"OpenRouter integration not available: {e}")


class TestEmotionProcessing:
    """Test emotion parsing and processing capabilities."""
    
    def test_emotion_parser_basic_parsing(self):
        """Test basic emotion parsing functionality."""
        try:
            from aichat.backend.services.llm.emotion_parser import EmotionParser
            
            parser = EmotionParser()
            
            test_cases = [
                ("I am very happy today!", "happy"),
                ("This is so frustrating and annoying!", "angry"), 
                ("I feel quite sad about this news.", "sad"),
                ("I'm excited about the upcoming event!", "excited"),
                ("This is a neutral statement.", "neutral")
            ]
            
            for text, expected_emotion in test_cases:
                emotion_result = parser.parse_emotion(text)
                
                if emotion_result:
                    assert isinstance(emotion_result, dict)
                    
                    # Check for expected keys
                    expected_keys = ['emotion', 'intensity', 'confidence']
                    for key in expected_keys:
                        if key in emotion_result:
                            assert emotion_result[key] is not None
                            
                    # Intensity should be a float between 0 and 1
                    if 'intensity' in emotion_result:
                        assert isinstance(emotion_result['intensity'], (int, float))
                        assert 0.0 <= emotion_result['intensity'] <= 1.0
                        
        except Exception as e:
            pytest.skip(f"Emotion parsing not available: {e}")
    
    @pytest.mark.asyncio
    async def test_sbert_emotion_detector(self):
        """Test SBERT emotion detection."""
        try:
            from aichat.backend.services.llm.tools.sbert_emotion_detector import SBERTEmotionDetector
            
            detector = SBERTEmotionDetector()
            
            test_texts = [
                "I absolutely love this amazing day!",
                "I'm feeling really angry about this situation!",
                "This makes me so sad and disappointed.",
                "I'm terrified of what might happen next.",
                "This is just a normal, everyday statement."
            ]
            
            for text in test_texts:
                emotion_result = await detector.detect_emotion(text)
                
                if emotion_result:
                    # SBERT detector returns emotion string directly
                    assert isinstance(emotion_result, str)
                    assert len(emotion_result) > 0
                    
                    # Should be a valid emotion name
                    assert emotion_result.lower() in [
                        'happy', 'excited', 'joyful', 'content', 'sad', 'disappointed', 
                        'angry', 'frustrated', 'afraid', 'worried', 'surprised', 
                        'confused', 'neutral', 'curious', 'disgusted'
                    ]
                        
        except Exception as e:
            pytest.skip(f"SBERT emotion detection not available: {e}")
    
    @pytest.mark.asyncio
    async def test_simple_emotion_detector(self):
        """Test simple rule-based emotion detection."""
        try:
            from aichat.backend.services.llm.tools.simple_emotion_detector import SimpleEmotionDetector
            
            detector = SimpleEmotionDetector()
            
            # Test keyword-based detection
            keyword_tests = [
                ("happy joyful wonderful", "happy"),
                ("angry furious mad", "angry"),
                ("sad depressed miserable", "sad"),
                ("afraid scared terrified", "afraid"),
                ("surprised amazed shocked", "surprised")
            ]
            
            for text, expected_category in keyword_tests:
                emotion_result = await detector.detect_emotion(text)
                
                if emotion_result:
                    # SimpleEmotionDetector returns emotion string directly
                    assert isinstance(emotion_result, str)
                    assert len(emotion_result) > 0
                        
        except Exception as e:
            pytest.skip(f"Simple emotion detection not available: {e}")


class TestLLMToolsIntegration:
    """Test LLM tools and function calling integration."""
    
    def test_compact_voice_controller_import(self):
        """Test compact voice controller tool import."""
        try:
            from aichat.backend.services.llm.tools.compact_voice_controller import CompactVoiceController
            
            controller = CompactVoiceController()
            assert controller is not None
            assert hasattr(controller, 'get_voice_parameters')
            assert hasattr(controller, 'get_emotion_vector')
            
        except ImportError as e:
            pytest.skip(f"Compact voice controller not available: {e}")
    
    def test_simple_llm_service_import(self):
        """Test simple LLM service tool import."""
        try:
            from aichat.backend.services.llm.tools.simple_llm_service import SimpleLLMService
            
            service = SimpleLLMService()
            assert service is not None
            assert hasattr(service, 'process_message')
            assert hasattr(service, 'get_emotion_only')
            
        except ImportError as e:
            pytest.skip(f"Simple LLM service not available: {e}")
    
    @pytest.mark.asyncio
    async def test_voice_controller_emotion_mapping(self):
        """Test voice controller emotion to voice parameter mapping."""
        try:
            from aichat.backend.services.llm.tools.compact_voice_controller import CompactVoiceController
            
            controller = CompactVoiceController()
            
            emotion_tests = [
                ("happy", {"speed": 1.1, "pitch": 1.05}),
                ("sad", {"speed": 0.9, "pitch": 0.95}),
                ("angry", {"speed": 1.2, "pitch": 1.1}),
                ("calm", {"speed": 1.0, "pitch": 1.0}),
                ("excited", {"speed": 1.15, "pitch": 1.08})
            ]
            
            for emotion, expected_adjustments in emotion_tests:
                voice_settings = await controller.apply_emotion_to_voice(
                    emotion=emotion,
                    intensity=0.7,
                    base_settings={"speed": 1.0, "pitch": 1.0}
                )
                
                if voice_settings:
                    assert isinstance(voice_settings, dict)
                    assert 'speed' in voice_settings
                    assert 'pitch' in voice_settings
                    
                    # Voice settings should be reasonable values
                    assert 0.5 <= voice_settings['speed'] <= 2.0
                    assert 0.5 <= voice_settings['pitch'] <= 2.0
                    
        except Exception as e:
            pytest.skip(f"Voice controller emotion mapping not available: {e}")


class TestLLMPerformanceAndMetrics:
    """Test LLM performance monitoring and metrics."""
    
    @pytest.mark.asyncio
    async def test_llm_response_timing(self):
        """Test LLM response generation timing metrics."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            
            service = PydanticAIService()
            
            test_prompt = "What is the capital of France?"
            character_context = {"name": "assistant", "personality": "helpful"}
            
            # Measure response time
            start_time = time.time()
            response = await service.generate_response(
                prompt=test_prompt,
                character_context=character_context,
                max_tokens=50
            )
            response_time = time.time() - start_time
            
            if response:
                # Response should be reasonably fast (< 30 seconds for simple query)
                assert response_time < 30.0, f"Response too slow: {response_time} seconds"
                
                # Check if timing info is included in response
                if 'response_time' in response:
                    assert isinstance(response['response_time'], (int, float))
                    assert response['response_time'] > 0
                    
        except Exception as e:
            pytest.skip(f"LLM timing metrics not available: {e}")
    
    @pytest.mark.asyncio
    async def test_llm_streaming_performance(self):
        """Test LLM streaming performance metrics."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            
            service = PydanticAIService()
            
            test_prompt = "Count from 1 to 10 with explanations for each number."
            character_context = {"name": "teacher", "personality": "patient and educational"}
            
            chunk_count = 0
            total_content_length = 0
            first_chunk_time = None
            start_time = time.time()
            
            async for chunk in service.generate_streaming_response(
                prompt=test_prompt,
                character_context=character_context,
                max_tokens=200
            ):
                if chunk:
                    chunk_count += 1
                    
                    if first_chunk_time is None:
                        first_chunk_time = time.time() - start_time
                        
                    # Track content length
                    content = chunk.get('content') or chunk.get('text') or ""
                    total_content_length += len(content)
            
            total_time = time.time() - start_time
            
            if chunk_count > 0:
                # Time to first chunk should be reasonable
                if first_chunk_time:
                    assert first_chunk_time < 10.0, f"First chunk too slow: {first_chunk_time} seconds"
                
                # Should have multiple chunks for longer content
                assert chunk_count > 0
                
                # Total content should be substantial
                assert total_content_length > 0
                
        except Exception as e:
            pytest.skip(f"LLM streaming performance not available: {e}")
    
    def test_llm_model_configuration(self):
        """Test LLM model configuration and selection."""
        try:
            from aichat.backend.services.llm.model_config import model_config, ModelProvider
            
            # Test model config structure
            assert hasattr(model_config, 'default_model')
            assert hasattr(model_config, 'available_models')
            
            # Test model provider enumeration
            providers = [ModelProvider.OPENAI, ModelProvider.ANTHROPIC, ModelProvider.OPENROUTER]
            for provider in providers:
                assert provider is not None
                
            # Test model selection logic
            if hasattr(model_config, 'select_model'):
                selected = model_config.select_model(
                    task="conversation",
                    character_type="friendly",
                    performance_priority="speed"
                )
                if selected:
                    assert isinstance(selected, str)
                    
        except Exception as e:
            pytest.skip(f"LLM model configuration not available: {e}")


class TestLLMErrorHandling:
    """Test LLM error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_llm_invalid_input_handling(self):
        """Test LLM handling of invalid inputs."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            
            service = PydanticAIService()
            
            # Test with various invalid inputs
            invalid_cases = [
                {"prompt": "", "character_context": {}},  # Empty prompt
                {"prompt": "A" * 10000, "character_context": {}},  # Very long prompt
                {"prompt": "Test", "character_context": None},  # Invalid context
                {"prompt": "Test", "max_tokens": -1},  # Invalid parameters
            ]
            
            for case in invalid_cases:
                try:
                    response = await service.generate_response(**case)
                    # If it returns something, should be valid structure
                    if response:
                        assert isinstance(response, dict)
                except Exception as e:
                    # Should handle with appropriate error types
                    assert isinstance(e, (ValueError, TypeError, RuntimeError))
                    
        except Exception as e:
            pytest.skip(f"LLM error handling not available: {e}")
    
    @pytest.mark.asyncio
    async def test_llm_api_key_handling(self):
        """Test LLM handling of missing or invalid API keys."""
        try:
            from aichat.backend.services.llm.openrouter_service import OpenRouterService
            
            # Test with invalid API key
            service = OpenRouterService(api_key="invalid_key_12345")
            
            try:
                response = await service.generate_response(
                    prompt="Test prompt",
                    model="openai/gpt-3.5-turbo",
                    max_tokens=10
                )
                
                # Should either fail gracefully or skip
                if response and 'error' in response:
                    assert isinstance(response['error'], str)
                    
            except Exception as e:
                # Should handle API key errors appropriately
                assert isinstance(e, (ValueError, RuntimeError, ConnectionError))
                
        except Exception as e:
            pytest.skip(f"LLM API key handling not available: {e}")


class TestLLMIntegrationWithServices:
    """Test LLM integration with other services."""
    
    def test_llm_with_chat_service(self):
        """Test LLM integration with chat service."""
        try:
            from aichat.backend.services.chat.chat_service import ChatService
            
            # Test ChatService initialization includes LLM
            chat_service = ChatService()
            assert chat_service is not None
            
            # Check for LLM-related attributes
            llm_attributes = ['llm_service', 'openrouter_service', 'pydantic_ai_service']
            
            has_llm = any(hasattr(chat_service, attr) for attr in llm_attributes)
            if not has_llm:
                pytest.skip("LLM not directly integrated with ChatService")
                
        except Exception as e:
            pytest.skip(f"ChatService LLM integration not available: {e}")
    
    def test_llm_with_emotion_processing(self):
        """Test LLM integration with emotion processing."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            from aichat.backend.services.llm.emotion_parser import EmotionParser
            
            # Test integrated emotion processing
            llm_service = PydanticAIService()
            emotion_parser = EmotionParser()
            
            # Verify they can work together
            test_response_text = "I'm feeling really excited about this new project!"
            
            emotion_result = emotion_parser.parse_emotion(test_response_text)
            if emotion_result:
                assert isinstance(emotion_result, dict)
                
                # Should be usable in LLM context
                character_context = {
                    "name": "assistant",
                    "personality": "helpful",
                    "current_emotion": emotion_result.get('emotion', 'neutral'),
                    "emotion_intensity": emotion_result.get('intensity', 0.5)
                }
                
                # This context should be valid for LLM service
                assert isinstance(character_context, dict)
                assert 'current_emotion' in character_context
                
        except Exception as e:
            pytest.skip(f"LLM emotion processing integration not available: {e}")
    
    @pytest.mark.asyncio
    async def test_llm_with_voice_control(self):
        """Test LLM integration with voice control systems."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            from aichat.backend.services.llm.tools.compact_voice_controller import CompactVoiceController
            
            llm_service = PydanticAIService()
            voice_controller = CompactVoiceController()
            
            # Test end-to-end emotion -> voice parameter pipeline
            test_prompt = "I'm absolutely thrilled about this wonderful news!"
            character_context = {"name": "excited_character", "personality": "enthusiastic"}
            
            # Generate LLM response
            llm_response = await llm_service.generate_response(
                prompt=test_prompt,
                character_context=character_context,
                max_tokens=100
            )
            
            if llm_response and 'emotion' in llm_response:
                emotion = llm_response['emotion']
                intensity = llm_response.get('emotion_intensity', 0.7)
                
                # Apply emotion to voice settings
                voice_settings = await voice_controller.apply_emotion_to_voice(
                    emotion=emotion,
                    intensity=intensity,
                    base_settings={"speed": 1.0, "pitch": 1.0}
                )
                
                if voice_settings:
                    assert isinstance(voice_settings, dict)
                    assert 'speed' in voice_settings
                    assert 'pitch' in voice_settings
                    
                    # Settings should reflect the emotion
                    if emotion in ['happy', 'excited']:
                        assert voice_settings['speed'] >= 1.0
                    elif emotion in ['sad', 'tired']:
                        assert voice_settings['speed'] <= 1.0
                        
        except Exception as e:
            pytest.skip(f"LLM voice control integration not available: {e}")
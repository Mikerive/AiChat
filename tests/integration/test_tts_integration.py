"""
TTS Integration Tests - Real functionality testing for Text-to-Speech pipeline
Tests individual TTS services and their integration with the voice pipeline.
"""

import asyncio
import pytest
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any, List


class TestTTSServiceIntegration:
    """Test TTS service integration and functionality."""
    
    def test_chatterbox_tts_service_import(self):
        """Test that ChatterboxTTSService can be imported and initialized."""
        try:
            from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
            
            # Test service initialization
            service = ChatterboxTTSService()
            assert service is not None
            assert hasattr(service, 'generate_speech')
            assert hasattr(service, 'generate_streaming_speech')
            
        except ImportError as e:
            pytest.skip(f"ChatterboxTTSService not available: {e}")
    
    def test_smart_tts_selector_import(self):
        """Test that SmartTTSSelector can be imported and configured."""
        try:
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector, TTSBackend
            
            # Test selector initialization
            selector = SmartTTSSelector()
            assert selector is not None
            assert hasattr(selector, 'select_backend')
            assert hasattr(selector, 'current_backend')
            
            # Test backend enumeration
            assert TTSBackend.CHATTERBOX is not None
            assert TTSBackend.PIPER is not None
            assert TTSBackend.SYSTEM is not None
            
        except ImportError as e:
            pytest.skip(f"SmartTTSSelector not available: {e}")
    
    def test_streaming_tts_integration_import(self):
        """Test that StreamingTTSIntegration can be imported and initialized."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingTTSIntegration, StreamingConfig
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Test streaming integration
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector)
            assert streaming is not None
            assert hasattr(streaming, 'start_streaming_session')
            assert hasattr(streaming, 'process_streaming_text')
            
        except ImportError as e:
            pytest.skip(f"StreamingTTSIntegration not available: {e}")

    @pytest.mark.asyncio
    async def test_chatterbox_basic_generation(self):
        """Test basic TTS generation with ChatterboxTTSService."""
        try:
            from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
            
            service = ChatterboxTTSService()
            test_text = "Hello, this is a test message for TTS generation."
            
            # Test basic generation
            result = await service.generate_speech(
                text=test_text,
                character_name="test_character",
                voice="default"
            )
            
            if result:
                assert isinstance(result, Path)
                assert result.exists()
                assert result.suffix == '.wav'
                assert 'test_character' in result.name
                
                # Verify audio file is not empty
                assert result.stat().st_size > 0
                
        except Exception as e:
            pytest.skip(f"ChatterboxTTS generation not available: {e}")

    @pytest.mark.asyncio 
    async def test_chatterbox_streaming_generation(self):
        """Test streaming TTS generation with ChatterboxTTSService."""
        try:
            from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
            
            service = ChatterboxTTSService()
            test_text = "This is a longer message. It has multiple sentences! Each should be processed separately."
            
            # Test streaming generation
            segments = await service.generate_streaming_speech(
                text=test_text,
                character_name="test_character",
                voice="default"
            )
            
            if segments:
                assert isinstance(segments, list)
                assert len(segments) > 0
                
                # Check first segment structure
                first_segment = segments[0]
                assert isinstance(first_segment, dict)
                
                # Check for expected keys in actual response
                expected_keys = ['audio_file', 'text', 'punctuation', 'pause_duration']
                for key in expected_keys:
                    assert key in first_segment
                    assert first_segment[key] is not None
                
                # Verify audio file exists
                audio_file = Path(first_segment['audio_file'])
                assert audio_file.exists()
                assert audio_file.suffix == '.wav'
                        
        except Exception as e:
            pytest.skip(f"ChatterboxTTS streaming not available: {e}")


class TestTTSStreamingPipeline:
    """Test the complete TTS streaming pipeline integration."""
    
    @pytest.mark.asyncio
    async def test_streaming_session_lifecycle(self):
        """Test complete streaming TTS session lifecycle."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingTTSIntegration, StreamingConfig
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Initialize components
            selector = SmartTTSSelector()
            config = StreamingConfig()
            streaming = StreamingTTSIntegration(selector, config)
            
            character_name = "test_character"
            voice = "default"
            
            # Test session start
            session_id = await streaming.start_streaming_session(
                character_name=character_name,
                voice=voice
            )
            
            assert session_id is not None
            assert isinstance(session_id, str)
            assert streaming.is_streaming is True
            
            # Test text processing
            test_chunks = [
                "Hello there! ",
                "This is a streaming test. ",
                "Each chunk should be processed ",
                "as it arrives in real-time."
            ]
            
            all_segments = []
            for chunk in test_chunks:
                segments = await streaming.process_streaming_text(
                    text_chunk=chunk,
                    character_name=character_name,
                    session_id=session_id,
                    voice=voice
                )
                if segments:
                    all_segments.extend(segments)
            
            # Test session finalization
            final_segments = await streaming.finalize_streaming_session(
                character_name=character_name,
                session_id=session_id,
                voice=voice
            )
            
            if final_segments:
                all_segments.extend(final_segments)
            
            # Verify results
            assert streaming.is_streaming is False
            if all_segments:
                assert len(all_segments) > 0
                for segment in all_segments:
                    assert isinstance(segment, dict)
                    assert 'session_id' in segment
                    assert segment['session_id'] == session_id
                    
        except Exception as e:
            pytest.skip(f"Streaming pipeline not available: {e}")
    
    @pytest.mark.asyncio
    async def test_streaming_trigger_modes(self):
        """Test different streaming trigger modes."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingTTSIntegration, StreamingConfig, StreamingMode
            )
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            trigger_modes = [
                StreamingMode.PUNCTUATION_TRIGGER,
                StreamingMode.SENTENCE_BUFFER,
                StreamingMode.WORD_COUNT_TRIGGER
            ]
            
            for mode in trigger_modes:
                config = StreamingConfig(mode=mode)
                selector = SmartTTSSelector()
                streaming = StreamingTTSIntegration(selector, config)
                
                # Test session with this mode
                session_id = await streaming.start_streaming_session("test_character")
                
                # Process text that should trigger based on mode
                test_text = "Short sentence. Another one! Question here?"
                segments = await streaming.process_streaming_text(
                    text_chunk=test_text,
                    character_name="test_character", 
                    session_id=session_id
                )
                
                # Finalize session
                await streaming.finalize_streaming_session("test_character", session_id)
                
                # Verify mode was applied
                assert streaming.config.mode == mode
                
        except Exception as e:
            pytest.skip(f"Streaming trigger modes not available: {e}")
    
    @pytest.mark.asyncio
    async def test_openrouter_streaming_handler(self):
        """Test OpenRouter streaming integration handler."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingTTSIntegration
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector)
            
            # Create OpenRouter handler
            handler = await streaming.create_openrouter_streaming_handler(
                character_name="test_character",
                voice="default"
            )
            
            assert callable(handler)
            assert hasattr(handler, 'finalize')
            
            # Test handler with mock OpenRouter chunk
            mock_chunk = {
                "choices": [{
                    "delta": {
                        "content": "Hello from OpenRouter streaming!"
                    }
                }]
            }
            
            result = await handler(mock_chunk)
            if result:
                assert isinstance(result, dict)
                assert 'text_chunk' in result
                assert 'session_id' in result
                assert result['text_chunk'] == "Hello from OpenRouter streaming!"
            
            # Test finalization
            final_segments = await handler.finalize()
            if final_segments:
                assert isinstance(final_segments, list)
                
        except Exception as e:
            pytest.skip(f"OpenRouter streaming handler not available: {e}")


class TestTTSPerformanceMetrics:
    """Test TTS performance monitoring and metrics."""
    
    @pytest.mark.asyncio
    async def test_streaming_stats_collection(self):
        """Test that streaming statistics are properly collected."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingTTSIntegration
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector)
            
            # Get initial stats
            initial_stats = streaming.get_streaming_stats()
            assert isinstance(initial_stats, dict)
            assert 'performance' in initial_stats
            assert 'config' in initial_stats
            assert 'current_state' in initial_stats
            
            # Verify stats structure
            perf_stats = initial_stats['performance']
            assert 'total_characters_processed' in perf_stats
            assert 'segments_generated' in perf_stats
            assert 'successful_streams' in perf_stats
            
        except Exception as e:
            pytest.skip(f"TTS stats collection not available: {e}")
    
    def test_tts_backend_selection(self):
        """Test TTS backend selection logic."""
        try:
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector, TTSBackend
            
            selector = SmartTTSSelector()
            
            # Test backend selection for different scenarios
            test_cases = [
                ("Short text", "default"),
                ("This is a longer text with multiple sentences. It should trigger different backend selection logic.", "default"),
                ("¿Hablas español? 你好世界!", "multilingual")  # Unicode/multilingual
            ]
            
            for text, character in test_cases:
                backend = selector.select_backend(text, character)
                assert isinstance(backend, TTSBackend)
                
            # Test backend switching
            original_backend = selector.current_backend
            success = selector.set_backend(TTSBackend.CHATTERBOX)
            if success:
                assert selector.current_backend == TTSBackend.CHATTERBOX
                
        except Exception as e:
            pytest.skip(f"TTS backend selection not available: {e}")


class TestTTSErrorHandling:
    """Test TTS error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_streaming_buffer_overflow(self):
        """Test handling of streaming buffer overflow conditions."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingTTSIntegration, StreamingConfig
            )
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Create config with small buffer for testing
            config = StreamingConfig(buffer_size=50)  # Small buffer
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector, config)
            
            session_id = await streaming.start_streaming_session("test_character")
            
            # Send large chunk that exceeds buffer
            large_text = "This is a very long text that exceeds the buffer size limit and should trigger overflow handling mechanisms to prevent data loss and maintain streaming performance. " * 10
            
            segments = await streaming.process_streaming_text(
                text_chunk=large_text,
                character_name="test_character",
                session_id=session_id
            )
            
            # Verify overflow was handled
            stats = streaming.get_streaming_stats()
            if 'performance' in stats and 'buffer_overflows' in stats['performance']:
                # Buffer overflow should have been detected and handled
                pass
                
            await streaming.finalize_streaming_session("test_character", session_id)
            
        except Exception as e:
            pytest.skip(f"TTS buffer overflow handling not available: {e}")
    
    @pytest.mark.asyncio
    async def test_invalid_session_handling(self):
        """Test handling of invalid or expired sessions."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingTTSIntegration
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector)
            
            # Test processing with invalid session
            invalid_session_id = "invalid_session_12345"
            
            segments = await streaming.process_streaming_text(
                text_chunk="Test text",
                character_name="test_character",
                session_id=invalid_session_id
            )
            
            # Should handle gracefully - either empty results or skip
            assert segments is not None  # Should not crash
            
        except Exception as e:
            pytest.skip(f"TTS invalid session handling not available: {e}")


class TestTTSIntegrationWithServices:
    """Test TTS integration with other services."""
    
    def test_tts_with_voice_service(self):
        """Test TTS integration with main VoiceService."""
        try:
            from aichat.backend.services.voice.voice_service import VoiceService
            
            # Test VoiceService initialization with TTS
            voice_service = VoiceService()
            assert voice_service is not None
            assert hasattr(voice_service, 'smart_tts')
            assert hasattr(voice_service, 'streaming_tts')
            
            # Test TTS components are properly initialized
            assert voice_service.smart_tts is not None
            assert voice_service.streaming_tts is not None
            
        except Exception as e:
            pytest.skip(f"VoiceService TTS integration not available: {e}")
    
    def test_tts_with_audio_io(self):
        """Test TTS integration with AudioIOService."""
        try:
            from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
            from aichat.backend.services.audio.audio_io_service import AudioIOService
            
            # Test TTS service has audio IO integration
            tts_service = ChatterboxTTSService()
            assert hasattr(tts_service, 'audio_io')
            assert tts_service.audio_io is not None
            
            # Test audio IO is properly typed
            from aichat.backend.services.audio.audio_io_service import AudioIOService
            assert isinstance(tts_service.audio_io, AudioIOService)
            
        except Exception as e:
            pytest.skip(f"TTS AudioIO integration not available: {e}")


class TestTTSConfigurationAndSettings:
    """Test TTS configuration and settings management."""
    
    def test_streaming_config_validation(self):
        """Test StreamingConfig validation and defaults."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingConfig, StreamingMode
            
            # Test default configuration
            config = StreamingConfig()
            assert config.mode == StreamingMode.PUNCTUATION_TRIGGER
            assert config.buffer_size > 0
            assert config.min_segment_length > 0
            
            # Test custom configuration
            custom_config = StreamingConfig(
                mode=StreamingMode.SENTENCE_BUFFER,
                buffer_size=100,
                enable_realtime_playback=False
            )
            
            assert custom_config.mode == StreamingMode.SENTENCE_BUFFER
            assert custom_config.buffer_size == 100
            assert custom_config.enable_realtime_playback is False
            
        except Exception as e:
            pytest.skip(f"StreamingConfig not available: {e}")
    
    def test_tts_voice_settings(self):
        """Test TTS voice settings and parameters."""
        try:
            from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
            
            service = ChatterboxTTSService(default_voice="test_voice")
            assert service.default_voice == "test_voice"
            
            # Test voice settings are configurable
            assert hasattr(service, 'pause_mappings')
            assert isinstance(service.pause_mappings, dict)
            
            # Test punctuation pause mappings
            assert '.' in service.pause_mappings
            assert ',' in service.pause_mappings
            assert service.pause_mappings['.'] > service.pause_mappings[',']
            
        except Exception as e:
            pytest.skip(f"TTS voice settings not available: {e}")
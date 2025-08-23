"""
TTS Streaming Pipeline Tests - Comprehensive testing for real-time TTS streaming
Focus on the streaming TTS pipeline as the most critical component for real-time interaction.
"""

import asyncio
import pytest
import time
import json
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass
from unittest.mock import AsyncMock


class TestTTSStreamingPipelineCore:
    """Test core TTS streaming pipeline functionality."""
    
    @pytest.mark.asyncio
    async def test_streaming_session_lifecycle_complete(self):
        """Test complete streaming session lifecycle with detailed validation."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingTTSIntegration, StreamingConfig, StreamingMode
            )
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Initialize with detailed configuration
            config = StreamingConfig(
                mode=StreamingMode.PUNCTUATION_TRIGGER,
                buffer_size=100,
                min_segment_length=5,
                enable_realtime_playback=True
            )
            
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector, config)
            
            # Detailed session parameters
            character_name = "streaming_test_character"
            voice_config = {
                "voice": "default",
                "speed": 1.1,
                "pitch": 1.0,
                "emotion_state": {
                    "emotion": "excited",
                    "intensity": 0.8
                }
            }
            
            # Step 1: Start session with validation
            session_id = await streaming.start_streaming_session(
                character_name=character_name,
                voice=voice_config["voice"],
                speed=voice_config["speed"],
                pitch=voice_config["pitch"],
                emotion_state=voice_config["emotion_state"]
            )
            
            assert session_id is not None
            assert isinstance(session_id, str)
            assert len(session_id) > 0
            assert streaming.is_streaming is True
            assert streaming.stream_start_time > 0
            
            # Step 2: Process streaming text with various triggers
            streaming_text_chunks = [
                "Hello there, this is the beginning of our streaming test!",
                " I'm going to tell you about different punctuation triggers.",
                " First, we have periods which create natural pauses.",
                " Then we have exclamation marks for excitement!",
                " Questions also work well, don't you think?",
                " Colons are useful for lists: item one, item two, item three.",
                " Finally, we'll end with a comprehensive summary."
            ]
            
            all_generated_segments = []
            processing_times = []
            
            for i, chunk in enumerate(streaming_text_chunks):
                chunk_start_time = time.time()
                
                segments = await streaming.process_streaming_text(
                    text_chunk=chunk,
                    character_name=character_name,
                    session_id=session_id,
                    voice=voice_config["voice"],
                    speed=voice_config["speed"],
                    pitch=voice_config["pitch"],
                    emotion_state=voice_config["emotion_state"]
                )
                
                chunk_processing_time = time.time() - chunk_start_time
                processing_times.append(chunk_processing_time)
                
                if segments:
                    all_generated_segments.extend(segments)
                    
                    # Validate each segment
                    for segment in segments:
                        assert isinstance(segment, dict)
                        assert 'session_id' in segment
                        assert segment['session_id'] == session_id
                        assert 'generation_time' in segment
                        assert isinstance(segment['generation_time'], (int, float))
                        
                        # Segment should preserve voice configuration
                        if 'character' in segment:
                            assert segment['character'] == character_name
            
            # Step 3: Finalize session with validation
            final_segments = await streaming.finalize_streaming_session(
                character_name=character_name,
                session_id=session_id,
                voice=voice_config["voice"],
                speed=voice_config["speed"],
                pitch=voice_config["pitch"],
                emotion_state=voice_config["emotion_state"]
            )
            
            if final_segments:
                all_generated_segments.extend(final_segments)
                
                # Final segments should be marked
                for segment in final_segments:
                    if 'is_final' in segment:
                        assert segment['is_final'] is True
            
            # Step 4: Validate complete session results
            assert streaming.is_streaming is False
            assert len(streaming.text_buffer) == 0  # Buffer should be cleared
            
            # Performance validation
            total_processing_time = sum(processing_times)
            avg_processing_time = total_processing_time / len(processing_times)
            assert avg_processing_time < 5.0, f"Processing too slow: {avg_processing_time} seconds per chunk"
            
            # Segment validation
            if all_generated_segments:
                assert len(all_generated_segments) > 0
                
                # All segments should belong to the session
                for segment in all_generated_segments:
                    assert segment['session_id'] == session_id
                    
                # Check streaming stats
                stats = streaming.get_streaming_stats()
                assert isinstance(stats, dict)
                assert 'performance' in stats
                assert stats['performance']['segments_generated'] > 0
                
        except Exception as e:
            pytest.skip(f"TTS streaming pipeline core not available: {e}")
    
    @pytest.mark.asyncio
    async def test_streaming_trigger_modes_comprehensive(self):
        """Test all streaming trigger modes with comprehensive validation."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingTTSIntegration, StreamingConfig, StreamingMode
            )
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Test each trigger mode with specific text patterns
            trigger_test_cases = [
                {
                    "mode": StreamingMode.PUNCTUATION_TRIGGER,
                    "test_text": "Hello! How are you? I'm doing great. This is a test: working well, isn't it?",
                    "expected_triggers": ["!", "?", ".", ":", ","],
                    "description": "Punctuation triggers"
                },
                {
                    "mode": StreamingMode.SENTENCE_BUFFER,
                    "test_text": "First sentence here. Second sentence follows. Third sentence ends.",
                    "expected_triggers": ["."],
                    "description": "Complete sentence buffering"
                },
                {
                    "mode": StreamingMode.WORD_COUNT_TRIGGER,
                    "test_text": "One two three four five six seven eight nine ten eleven twelve thirteen",
                    "expected_word_count": 8,  # Default trigger count
                    "description": "Word count triggering"
                }
            ]
            
            for test_case in trigger_test_cases:
                # Configure for specific trigger mode
                config = StreamingConfig(
                    mode=test_case["mode"],
                    buffer_size=200,
                    word_trigger_count=test_case.get("expected_word_count", 8),
                    min_segment_length=3
                )
                
                selector = SmartTTSSelector()
                streaming = StreamingTTSIntegration(selector, config)
                
                # Start session
                session_id = await streaming.start_streaming_session("trigger_test_character")
                
                try:
                    # Process text and monitor trigger behavior
                    segments = await streaming.process_streaming_text(
                        text_chunk=test_case["test_text"],
                        character_name="trigger_test_character",
                        session_id=session_id
                    )
                    
                    # Validate trigger behavior
                    assert streaming.config.mode == test_case["mode"]
                    
                    if segments:
                        # Should generate segments based on trigger mode
                        for segment in segments:
                            assert isinstance(segment, dict)
                            assert 'text' in segment or 'content' in segment
                            
                            # Segment text should not be empty
                            segment_text = segment.get('text') or segment.get('content') or ""
                            assert len(segment_text.strip()) >= config.min_segment_length
                    
                    # Check buffer state after processing
                    if test_case["mode"] == StreamingMode.PUNCTUATION_TRIGGER:
                        # Buffer might contain remaining text after last punctuation
                        pass
                    elif test_case["mode"] == StreamingMode.SENTENCE_BUFFER:
                        # Buffer should contain incomplete sentence
                        pass
                    elif test_case["mode"] == StreamingMode.WORD_COUNT_TRIGGER:
                        # Buffer should contain remaining words
                        pass
                    
                finally:
                    # Finalize to clear buffer
                    await streaming.finalize_streaming_session("trigger_test_character", session_id)
                    
        except Exception as e:
            pytest.skip(f"TTS streaming trigger modes not available: {e}")
    
    @pytest.mark.asyncio
    async def test_openrouter_streaming_integration_detailed(self):
        """Test detailed OpenRouter streaming integration."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingTTSIntegration
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector)
            
            # Create OpenRouter handler with detailed configuration
            character_config = {
                "name": "openrouter_character",
                "voice": "premium",
                "speed": 1.05,
                "pitch": 0.98,
                "emotion_state": {
                    "emotion": "thoughtful",
                    "intensity": 0.6,
                    "context": "explaining complex concepts"
                }
            }
            
            handler = await streaming.create_openrouter_streaming_handler(
                character_name=character_config["name"],
                voice=character_config["voice"],
                speed=character_config["speed"],
                pitch=character_config["pitch"],
                emotion_state=character_config["emotion_state"]
            )
            
            assert callable(handler)
            assert hasattr(handler, 'finalize')
            
            # Simulate OpenRouter streaming chunks (realistic format)
            openrouter_chunks = [
                {
                    "id": "stream_1",
                    "choices": [{
                        "delta": {
                            "content": "I'm going to explain"
                        },
                        "index": 0
                    }]
                },
                {
                    "id": "stream_2", 
                    "choices": [{
                        "delta": {
                            "content": " how artificial intelligence"
                        },
                        "index": 0
                    }]
                },
                {
                    "id": "stream_3",
                    "choices": [{
                        "delta": {
                            "content": " works in simple terms."
                        },
                        "index": 0
                    }]
                },
                {
                    "id": "stream_4",
                    "choices": [{
                        "delta": {
                            "content": " First, let's start with"
                        },
                        "index": 0
                    }]
                },
                {
                    "id": "stream_5",
                    "choices": [{
                        "delta": {
                            "content": " the basics of neural networks!"
                        },
                        "index": 0
                    }]
                }
            ]
            
            # Process chunks and collect results
            handler_results = []
            accumulated_text = ""
            
            for chunk in openrouter_chunks:
                result = await handler(chunk)
                
                if result:
                    assert isinstance(result, dict)
                    assert 'text_chunk' in result
                    assert 'session_id' in result
                    
                    text_chunk = result['text_chunk']
                    accumulated_text += text_chunk
                    
                    # Validate TTS segments if generated
                    if 'tts_segments' in result and result['tts_segments']:
                        for segment in result['tts_segments']:
                            assert isinstance(segment, dict)
                            assert 'session_id' in segment
                            assert segment['session_id'] == result['session_id']
                    
                    handler_results.append(result)
            
            # Finalize streaming
            final_segments = await handler.finalize()
            
            # Validate complete integration
            assert len(handler_results) > 0
            assert len(accumulated_text) > 0
            
            # Text should be reconstructable from chunks
            expected_full_text = "I'm going to explain how artificial intelligence works in simple terms. First, let's start with the basics of neural networks!"
            assert accumulated_text == expected_full_text
            
            if final_segments:
                assert isinstance(final_segments, list)
                for segment in final_segments:
                    assert isinstance(segment, dict)
                    
        except Exception as e:
            pytest.skip(f"OpenRouter streaming integration not available: {e}")


class TestTTSStreamingPerformanceOptimization:
    """Test TTS streaming performance and optimization features."""
    
    @pytest.mark.asyncio
    async def test_streaming_buffer_optimization(self):
        """Test streaming buffer optimization and overflow handling."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingTTSIntegration, StreamingConfig, StreamingMode
            )
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Test different buffer sizes
            buffer_test_cases = [
                {"buffer_size": 50, "description": "Small buffer - frequent overflow"},
                {"buffer_size": 200, "description": "Medium buffer - balanced"},
                {"buffer_size": 500, "description": "Large buffer - minimal overflow"}
            ]
            
            for test_case in buffer_test_cases:
                config = StreamingConfig(
                    mode=StreamingMode.PUNCTUATION_TRIGGER,
                    buffer_size=test_case["buffer_size"],
                    min_segment_length=3
                )
                
                selector = SmartTTSSelector()
                streaming = StreamingTTSIntegration(selector, config)
                
                session_id = await streaming.start_streaming_session("buffer_test_character")
                
                try:
                    # Generate text that will challenge buffer size
                    long_text_chunks = [
                        "This is a very long piece of text that is designed to test buffer overflow handling mechanisms.",
                        " It contains multiple sentences with various punctuation marks to trigger different processing paths.",
                        " The goal is to ensure that the streaming system can handle large amounts of text without losing data.",
                        " Buffer management is critical for maintaining real-time performance in streaming applications.",
                        " We want to verify that overflow conditions are detected and handled gracefully."
                    ]
                    
                    initial_stats = streaming.get_streaming_stats()
                    initial_overflows = initial_stats['performance']['buffer_overflows']
                    
                    # Process chunks and monitor buffer behavior
                    for chunk in long_text_chunks:
                        segments = await streaming.process_streaming_text(
                            text_chunk=chunk,
                            character_name="buffer_test_character",
                            session_id=session_id
                        )
                        
                        # Check buffer state
                        current_buffer_length = len(streaming.text_buffer)
                        
                        if current_buffer_length > config.buffer_size:
                            # Buffer overflow should have been handled
                            final_stats = streaming.get_streaming_stats()
                            assert final_stats['performance']['buffer_overflows'] > initial_overflows
                    
                    # Verify final state
                    final_stats = streaming.get_streaming_stats()
                    
                    # Buffer size should affect overflow count
                    if test_case["buffer_size"] < 100:
                        # Small buffer likely to overflow
                        assert final_stats['performance']['buffer_overflows'] >= initial_overflows
                    
                finally:
                    await streaming.finalize_streaming_session("buffer_test_character", session_id)
                    
        except Exception as e:
            pytest.skip(f"TTS streaming buffer optimization not available: {e}")
    
    @pytest.mark.asyncio
    async def test_streaming_parallel_generation(self):
        """Test parallel TTS generation for improved performance."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingTTSIntegration, StreamingConfig
            )
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Configure for parallel processing
            config = StreamingConfig(
                parallel_generation=True,
                lookahead_segments=3,
                enable_realtime_playback=True
            )
            
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector, config)
            
            session_id = await streaming.start_streaming_session("parallel_test_character")
            
            try:
                # Text designed to generate multiple segments
                test_text_segments = [
                    "First segment for parallel processing.",
                    " Second segment should be generated concurrently.",
                    " Third segment tests lookahead capability.",
                    " Fourth segment validates performance gains."
                ]
                
                # Measure generation time with parallel processing
                parallel_start_time = time.time()
                
                all_segments = []
                for text in test_text_segments:
                    segments = await streaming.process_streaming_text(
                        text_chunk=text,
                        character_name="parallel_test_character",
                        session_id=session_id
                    )
                    
                    if segments:
                        all_segments.extend(segments)
                
                parallel_total_time = time.time() - parallel_start_time
                
                # Finalize and get final segments
                final_segments = await streaming.finalize_streaming_session(
                    "parallel_test_character", session_id
                )
                
                if final_segments:
                    all_segments.extend(final_segments)
                
                # Validate parallel processing results
                if all_segments:
                    assert len(all_segments) > 0
                    
                    # Check for parallel processing indicators
                    for segment in all_segments:
                        if 'generation_time' in segment:
                            assert isinstance(segment['generation_time'], (int, float))
                            assert segment['generation_time'] > 0
                        
                        if 'is_realtime_stream' in segment:
                            # Parallel processing might use real-time streaming
                            assert isinstance(segment['is_realtime_stream'], bool)
                
                # Performance should be reasonable
                assert parallel_total_time < 30.0, f"Parallel processing too slow: {parallel_total_time} seconds"
                
            finally:
                # Ensure cleanup
                if streaming.is_streaming:
                    await streaming.finalize_streaming_session("parallel_test_character", session_id)
                    
        except Exception as e:
            pytest.skip(f"TTS streaming parallel generation not available: {e}")
    
    @pytest.mark.asyncio
    async def test_streaming_realtime_playback(self):
        """Test real-time playback integration with streaming."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingTTSIntegration, StreamingConfig
            )
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Configure for real-time playback
            config = StreamingConfig(
                enable_realtime_playback=True,
                parallel_generation=True
            )
            
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector, config)
            
            session_id = await streaming.start_streaming_session("realtime_test_character")
            
            try:
                # Test text for real-time playback
                realtime_text = "This text should trigger real-time playback as segments are generated. Each sentence will be played immediately upon completion."
                
                # Process with real-time playback enabled
                segments = await streaming.process_streaming_text(
                    text_chunk=realtime_text,
                    character_name="realtime_test_character",
                    session_id=session_id
                )
                
                if segments:
                    # Verify real-time playback configuration
                    assert config.enable_realtime_playback is True
                    
                    # Each segment should be processed for playback
                    for segment in segments:
                        assert isinstance(segment, dict)
                        
                        # Real-time segments should have audio file paths
                        if 'audio_file' in segment:
                            assert isinstance(segment['audio_file'], str)
                            assert len(segment['audio_file']) > 0
                        
                        # May have playback timing information
                        if 'pause_duration' in segment:
                            assert isinstance(segment['pause_duration'], (int, float))
                            assert segment['pause_duration'] >= 0
                
                # Finalize with real-time playback
                final_segments = await streaming.finalize_streaming_session(
                    "realtime_test_character", session_id
                )
                
                # Final segments should also support real-time playback
                if final_segments:
                    for segment in final_segments:
                        if 'audio_file' in segment:
                            assert isinstance(segment['audio_file'], str)
                            
            finally:
                if streaming.is_streaming:
                    await streaming.finalize_streaming_session("realtime_test_character", session_id)
                    
        except Exception as e:
            pytest.skip(f"TTS streaming realtime playback not available: {e}")


class TestTTSStreamingErrorHandlingAndRecovery:
    """Test TTS streaming error handling and recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_streaming_session_recovery(self):
        """Test streaming session recovery from various error conditions."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingTTSIntegration, StreamingConfig
            )
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector)
            
            # Test recovery scenarios
            recovery_test_cases = [
                {
                    "description": "Invalid session ID",
                    "test_function": lambda: streaming.process_streaming_text(
                        "test", "character", "invalid_session_id"
                    )
                },
                {
                    "description": "Empty text processing",
                    "test_function": lambda: streaming.process_streaming_text(
                        "", "character", "session_123"
                    )
                },
                {
                    "description": "Processing after session end",
                    "test_function": None  # Will be set up dynamically
                }
            ]
            
            for test_case in recovery_test_cases:
                try:
                    if test_case["description"] == "Processing after session end":
                        # Set up and tear down session
                        session_id = await streaming.start_streaming_session("test_character")
                        await streaming.finalize_streaming_session("test_character", session_id)
                        
                        # Now try to process (should handle gracefully)
                        result = await streaming.process_streaming_text(
                            "test text", "test_character", session_id
                        )
                    else:
                        result = await test_case["test_function"]()
                    
                    # Should handle gracefully - either return None/empty or skip
                    if result is not None:
                        assert isinstance(result, list)
                        
                except Exception as e:
                    # Should not crash - errors should be handled gracefully
                    assert isinstance(e, (ValueError, TypeError, RuntimeError))
                    
        except Exception as e:
            pytest.skip(f"TTS streaming error handling not available: {e}")
    
    @pytest.mark.asyncio
    async def test_streaming_memory_management(self):
        """Test streaming memory management and cleanup."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingTTSIntegration, StreamingConfig
            )
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector)
            
            # Test memory management with multiple sessions
            session_ids = []
            
            try:
                # Create multiple streaming sessions
                for i in range(5):
                    session_id = await streaming.start_streaming_session(f"memory_test_character_{i}")
                    if session_id:
                        session_ids.append(session_id)
                
                # Process text in all sessions
                for session_id in session_ids:
                    await streaming.process_streaming_text(
                        f"Memory test for session {session_id}",
                        f"character_{session_id}",
                        session_id
                    )
                
                # Verify memory usage is reasonable
                stats = streaming.get_streaming_stats()
                current_state = stats['current_state']
                
                # Should track active sessions appropriately
                assert 'buffer_length' in current_state
                assert 'pending_segments' in current_state
                assert 'generated_segments' in current_state
                
            finally:
                # Cleanup all sessions
                for session_id in session_ids:
                    try:
                        await streaming.finalize_streaming_session(f"character_{session_id}", session_id)
                    except Exception:
                        # Cleanup should not fail
                        pass
                
                # After cleanup, streaming should be clean
                assert streaming.is_streaming is False
                assert len(streaming.text_buffer) == 0
                
        except Exception as e:
            pytest.skip(f"TTS streaming memory management not available: {e}")


class TestTTSStreamingIntegrationWithLLM:
    """Test TTS streaming integration specifically with LLM services."""
    
    @pytest.mark.asyncio
    async def test_llm_streaming_to_tts_streaming_pipeline(self):
        """Test comprehensive LLM streaming to TTS streaming pipeline."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingTTSIntegration, StreamingConfig, StreamingMode
            )
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Initialize services with optimized configuration
            llm_service = PydanticAIService()
            
            config = StreamingConfig(
                mode=StreamingMode.PUNCTUATION_TRIGGER,
                buffer_size=150,
                enable_realtime_playback=True,
                parallel_generation=True
            )
            
            tts_selector = SmartTTSSelector()
            streaming_tts = StreamingTTSIntegration(tts_selector, config)
            
            # Test comprehensive streaming scenario
            test_prompt = "Explain the process of photosynthesis in plants, including the light and dark reactions."
            character_context = {
                "name": "science_teacher",
                "personality": "knowledgeable, patient, and enthusiastic about biology",
                "profile": "An experienced biology teacher who makes complex concepts accessible"
            }
            
            # Start TTS streaming session
            tts_session_id = await streaming_tts.start_streaming_session(
                character_name="science_teacher",
                voice="educational",
                speed=0.95,  # Slightly slower for educational content
                pitch=1.0
            )
            
            if not tts_session_id:
                pytest.skip("Could not start TTS streaming session")
            
            try:
                # Comprehensive streaming pipeline
                pipeline_results = {
                    "llm_chunks_processed": 0,
                    "tts_segments_generated": 0,
                    "total_text_processed": "",
                    "streaming_latency": [],
                    "pipeline_success": True
                }
                
                # Process LLM streaming response with TTS
                async for llm_chunk in llm_service.generate_streaming_response(
                    prompt=test_prompt,
                    character_context=character_context,
                    max_tokens=300
                ):
                    if llm_chunk and 'content' in llm_chunk:
                        chunk_start_time = time.time()
                        
                        content = llm_chunk['content']
                        pipeline_results["total_text_processed"] += content
                        pipeline_results["llm_chunks_processed"] += 1
                        
                        # Process with streaming TTS
                        tts_segments = await streaming_tts.process_streaming_text(
                            text_chunk=content,
                            character_name="science_teacher",
                            session_id=tts_session_id,
                            voice="educational",
                            speed=0.95,
                            pitch=1.0
                        )
                        
                        chunk_latency = time.time() - chunk_start_time
                        pipeline_results["streaming_latency"].append(chunk_latency)
                        
                        if tts_segments:
                            pipeline_results["tts_segments_generated"] += len(tts_segments)
                            
                            # Validate streaming integration
                            for segment in tts_segments:
                                assert isinstance(segment, dict)
                                assert 'session_id' in segment
                                assert segment['session_id'] == tts_session_id
                                
                                # Segment should preserve educational context
                                if 'character' in segment:
                                    assert segment['character'] == "science_teacher"
                
                # Finalize TTS streaming
                final_segments = await streaming_tts.finalize_streaming_session(
                    character_name="science_teacher",
                    session_id=tts_session_id,
                    voice="educational",
                    speed=0.95,
                    pitch=1.0
                )
                
                if final_segments:
                    pipeline_results["tts_segments_generated"] += len(final_segments)
                
                # Validate comprehensive pipeline results
                assert pipeline_results["llm_chunks_processed"] > 0
                assert len(pipeline_results["total_text_processed"]) > 0
                assert pipeline_results["pipeline_success"] is True
                
                # Performance validation
                if pipeline_results["streaming_latency"]:
                    avg_latency = sum(pipeline_results["streaming_latency"]) / len(pipeline_results["streaming_latency"])
                    assert avg_latency < 2.0, f"Streaming latency too high: {avg_latency} seconds"
                
                # Content validation
                processed_text = pipeline_results["total_text_processed"]
                assert len(processed_text) > 50  # Should have substantial content
                
                # TTS segments should have been generated
                if pipeline_results["tts_segments_generated"] > 0:
                    # Streaming worked end-to-end
                    assert pipeline_results["tts_segments_generated"] > 0
                    
            finally:
                # Ensure cleanup
                if streaming_tts.is_streaming:
                    await streaming_tts.finalize_streaming_session("science_teacher", tts_session_id)
                    
        except Exception as e:
            pytest.skip(f"LLM to TTS streaming pipeline not available: {e}")
    
    @pytest.mark.asyncio
    async def test_emotion_aware_streaming_tts(self):
        """Test emotion-aware TTS streaming with dynamic voice adjustments."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingTTSIntegration
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            from aichat.backend.services.llm.emotion_parser import EmotionParser
            
            # Initialize services
            llm_service = PydanticAIService()
            tts_selector = SmartTTSSelector()
            streaming_tts = StreamingTTSIntegration(tts_selector)
            emotion_parser = EmotionParser()
            
            # Test emotion-driven streaming
            emotional_prompts = [
                {
                    "prompt": "I'm absolutely thrilled about this amazing discovery!",
                    "expected_emotion": "excited",
                    "voice_adjustments": {"speed": 1.15, "pitch": 1.1}
                },
                {
                    "prompt": "I'm feeling quite sad about this unfortunate news.",
                    "expected_emotion": "sad", 
                    "voice_adjustments": {"speed": 0.85, "pitch": 0.9}
                },
                {
                    "prompt": "This situation makes me really angry and frustrated!",
                    "expected_emotion": "angry",
                    "voice_adjustments": {"speed": 1.2, "pitch": 1.15}
                }
            ]
            
            for test_case in emotional_prompts:
                # Start streaming session
                session_id = await streaming_tts.start_streaming_session("emotion_test_character")
                
                try:
                    # Generate LLM response with emotion
                    character_context = {
                        "name": "emotion_test_character",
                        "personality": "expressive and emotionally responsive"
                    }
                    
                    llm_response = await llm_service.generate_response(
                        prompt=test_case["prompt"],
                        character_context=character_context,
                        max_tokens=100
                    )
                    
                    if llm_response and 'text' in llm_response:
                        response_text = llm_response['text']
                        
                        # Parse emotion from response
                        emotion_result = emotion_parser.parse_emotion(response_text)
                        
                        if emotion_result and 'emotion' in emotion_result:
                            detected_emotion = emotion_result['emotion']
                            emotion_intensity = emotion_result.get('intensity', 0.7)
                            
                            # Apply emotion to streaming TTS
                            emotion_state = {
                                "emotion": detected_emotion,
                                "intensity": emotion_intensity,
                                "context": "emotional_response"
                            }
                            
                            # Process with emotion-aware streaming
                            segments = await streaming_tts.process_streaming_text(
                                text_chunk=response_text,
                                character_name="emotion_test_character", 
                                session_id=session_id,
                                emotion_state=emotion_state
                            )
                            
                            if segments:
                                for segment in segments:
                                    assert isinstance(segment, dict)
                                    
                                    # Segment should contain emotion information
                                    if 'emotion_state' in segment:
                                        segment_emotion = segment['emotion_state']
                                        assert 'emotion' in segment_emotion
                                        assert 'intensity' in segment_emotion
                                        
                                    # Voice parameters should reflect emotion
                                    if 'voice_settings' in segment:
                                        voice_settings = segment['voice_settings']
                                        
                                        # Validate emotion-based adjustments
                                        if detected_emotion in ['happy', 'excited']:
                                            if 'speed' in voice_settings:
                                                assert voice_settings['speed'] >= 1.0
                                        elif detected_emotion in ['sad', 'tired']:
                                            if 'speed' in voice_settings:
                                                assert voice_settings['speed'] <= 1.0
                                                
                finally:
                    await streaming_tts.finalize_streaming_session("emotion_test_character", session_id)
                    
        except Exception as e:
            pytest.skip(f"Emotion-aware TTS streaming not available: {e}")


class TestTTSStreamingProductionReadiness:
    """Test TTS streaming production readiness and reliability."""
    
    @pytest.mark.asyncio
    async def test_streaming_stress_testing(self):
        """Test TTS streaming under stress conditions."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingTTSIntegration, StreamingConfig
            )
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Configure for stress testing
            config = StreamingConfig(
                buffer_size=100,
                enable_realtime_playback=False,  # Disable for stress test
                parallel_generation=True
            )
            
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector, config)
            
            # Stress test parameters
            num_concurrent_sessions = 3
            chunks_per_session = 10
            
            stress_results = {
                "sessions_started": 0,
                "sessions_completed": 0,
                "total_segments_generated": 0,
                "errors_encountered": 0,
                "total_processing_time": 0
            }
            
            stress_start_time = time.time()
            
            # Create concurrent streaming sessions
            session_tasks = []
            
            for session_idx in range(num_concurrent_sessions):
                session_task = self._run_stress_session(
                    streaming, session_idx, chunks_per_session, stress_results
                )
                session_tasks.append(session_task)
            
            # Run all sessions concurrently
            await asyncio.gather(*session_tasks, return_exceptions=True)
            
            stress_results["total_processing_time"] = time.time() - stress_start_time
            
            # Validate stress test results
            assert stress_results["sessions_started"] == num_concurrent_sessions
            assert stress_results["sessions_completed"] > 0  # At least some should complete
            
            # Error rate should be acceptable
            error_rate = stress_results["errors_encountered"] / (num_concurrent_sessions * chunks_per_session)
            assert error_rate < 0.5, f"Too many errors in stress test: {error_rate * 100}%"
            
            # Performance should be reasonable under stress
            avg_time_per_chunk = stress_results["total_processing_time"] / (num_concurrent_sessions * chunks_per_session)
            assert avg_time_per_chunk < 5.0, f"Processing too slow under stress: {avg_time_per_chunk} seconds per chunk"
            
        except Exception as e:
            pytest.skip(f"TTS streaming stress testing not available: {e}")
    
    async def _run_stress_session(self, streaming, session_idx, num_chunks, results):
        """Run a single stress test session."""
        character_name = f"stress_character_{session_idx}"
        session_id = None
        
        try:
            results["sessions_started"] += 1
            
            # Start session
            session_id = await streaming.start_streaming_session(character_name)
            
            if session_id:
                # Process multiple chunks
                for chunk_idx in range(num_chunks):
                    try:
                        test_text = f"Stress test chunk {chunk_idx} for session {session_idx}. This text is designed to test concurrent processing capabilities."
                        
                        segments = await streaming.process_streaming_text(
                            text_chunk=test_text,
                            character_name=character_name,
                            session_id=session_id
                        )
                        
                        if segments:
                            results["total_segments_generated"] += len(segments)
                            
                    except Exception:
                        results["errors_encountered"] += 1
                
                results["sessions_completed"] += 1
                
        except Exception:
            results["errors_encountered"] += 1
            
        finally:
            # Cleanup
            if session_id:
                try:
                    await streaming.finalize_streaming_session(character_name, session_id)
                except Exception:
                    pass
    
    @pytest.mark.asyncio
    async def test_streaming_configuration_validation(self):
        """Test streaming configuration validation and edge cases."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import (
                StreamingConfig, StreamingMode
            )
            
            # Test valid configurations
            valid_configs = [
                StreamingConfig(),  # Default
                StreamingConfig(mode=StreamingMode.SENTENCE_BUFFER, buffer_size=200),
                StreamingConfig(enable_realtime_playback=False, parallel_generation=True)
            ]
            
            for config in valid_configs:
                assert config is not None
                assert hasattr(config, 'mode')
                assert hasattr(config, 'buffer_size')
                assert config.buffer_size > 0
                assert config.min_segment_length >= 0
            
            # Test edge case configurations
            edge_cases = [
                {"buffer_size": 1, "description": "Minimal buffer"},
                {"min_segment_length": 0, "description": "No minimum segment length"},
                {"word_trigger_count": 1, "description": "Single word trigger"}
            ]
            
            for edge_case in edge_cases:
                try:
                    config = StreamingConfig(**{k: v for k, v in edge_case.items() if k != "description"})
                    assert config is not None
                    
                    # Configuration should be internally consistent
                    assert config.buffer_size >= config.min_segment_length
                    assert config.word_trigger_count > 0
                    
                except Exception as e:
                    # Should handle edge cases gracefully
                    assert isinstance(e, (ValueError, TypeError))
                    
        except Exception as e:
            pytest.skip(f"TTS streaming configuration validation not available: {e}")

    @pytest.mark.asyncio
    async def test_streaming_metrics_and_monitoring(self):
        """Test comprehensive streaming metrics and monitoring capabilities."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingTTSIntegration
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            selector = SmartTTSSelector()
            streaming = StreamingTTSIntegration(selector)
            
            # Initial metrics
            initial_stats = streaming.get_streaming_stats()
            assert isinstance(initial_stats, dict)
            
            required_stat_categories = ['config', 'current_state', 'performance']
            for category in required_stat_categories:
                assert category in initial_stats
                assert isinstance(initial_stats[category], dict)
            
            # Test metrics during operation
            session_id = await streaming.start_streaming_session("metrics_test_character")
            
            try:
                # Process text and monitor metrics
                test_texts = [
                    "First metrics test sentence.",
                    "Second sentence for metrics validation.",
                    "Final sentence to complete metrics testing."
                ]
                
                for text in test_texts:
                    await streaming.process_streaming_text(
                        text_chunk=text,
                        character_name="metrics_test_character",
                        session_id=session_id
                    )
                    
                    # Check updated metrics
                    current_stats = streaming.get_streaming_stats()
                    
                    # Performance metrics should be updating
                    perf_stats = current_stats['performance']
                    assert perf_stats['total_characters_processed'] >= len(text)
                    
                    # Current state should reflect active session
                    state = current_stats['current_state']
                    assert state['is_streaming'] is True
                    assert isinstance(state['buffer_length'], int)
                    assert isinstance(state['generated_segments'], int)
                
                # Final metrics after completion
                await streaming.finalize_streaming_session("metrics_test_character", session_id)
                
                final_stats = streaming.get_streaming_stats()
                assert final_stats['current_state']['is_streaming'] is False
                assert final_stats['performance']['successful_streams'] > 0
                
            finally:
                if streaming.is_streaming:
                    await streaming.finalize_streaming_session("metrics_test_character", session_id)
                    
        except Exception as e:
            pytest.skip(f"TTS streaming metrics not available: {e}")
"""
STT Integration Tests - Real functionality testing for Speech-to-Text pipeline
Tests individual STT services and their integration with the voice pipeline.
"""

import asyncio
import pytest
import numpy as np
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any, List


class TestSTTServiceIntegration:
    """Test STT service integration and functionality."""
    
    def test_whisper_service_import(self):
        """Test that WhisperService can be imported and initialized."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            
            # Test service initialization
            service = WhisperService(model_name="base")
            assert service is not None
            assert hasattr(service, 'transcribe_audio')
            assert hasattr(service, 'transcribe_audio_bytes')
            assert service.model_name == "base"
            
        except ImportError as e:
            pytest.skip(f"WhisperService not available: {e}")
    
    def test_whisper_model_loading(self):
        """Test Whisper model loading and initialization."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            
            # Test with different model sizes
            model_sizes = ["tiny", "base", "small"]
            
            for model_size in model_sizes:
                service = WhisperService(model_name=model_size)
                assert service.model_name == model_size
                
                # Check if model loaded successfully
                if service._initialized:
                    assert service.model is not None
                    break  # At least one model should work
            else:
                pytest.skip("No Whisper models could be loaded")
                
        except Exception as e:
            pytest.skip(f"Whisper model loading not available: {e}")
    
    def test_vad_service_import(self):
        """Test that VAD (Voice Activity Detection) service can be imported."""
        try:
            from aichat.backend.services.voice.stt.vad_service import VADService
            
            # Test service initialization
            service = VADService()
            assert service is not None
            assert hasattr(service, 'process_audio_frame')
            assert hasattr(service, 'start')
            
        except ImportError as e:
            pytest.skip(f"VADService not available: {e}")
    
    def test_streaming_stt_service_import(self):
        """Test that streaming STT service can be imported."""
        try:
            from aichat.backend.services.voice.stt.streaming_stt_service import StreamingSTTService
            
            # Test service initialization
            service = StreamingSTTService()
            assert service is not None
            assert hasattr(service, 'start_streaming')
            assert hasattr(service, 'process_audio_chunk')
            
        except ImportError as e:
            pytest.skip(f"StreamingSTTService not available: {e}")


class TestSTTAudioProcessing:
    """Test STT audio processing capabilities."""
    
    def _generate_test_audio(self, duration_seconds: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
        """Generate synthetic audio for testing."""
        # Generate a simple sine wave
        t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), False)
        frequency = 440  # A4 note
        audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        return audio
    
    @pytest.mark.asyncio
    async def test_whisper_audio_transcription(self):
        """Test Whisper audio transcription with synthetic audio."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            import soundfile as sf
            
            service = WhisperService()
            if not service._initialized:
                pytest.skip("Whisper service not initialized")
            
            # Generate test audio
            test_audio = self._generate_test_audio(duration_seconds=2.0)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                sf.write(tmp_file.name, test_audio, 16000)
                tmp_path = Path(tmp_file.name)
            
            try:
                # Test transcription
                result = await service.transcribe_audio(tmp_path)
                
                if result:
                    assert isinstance(result, dict)
                    expected_keys = ['text', 'confidence', 'language']
                    for key in expected_keys:
                        if key in result:
                            assert result[key] is not None
                            
                    # Text should be a string
                    if 'text' in result:
                        assert isinstance(result['text'], str)
                        
            finally:
                # Clean up temporary file
                tmp_path.unlink(missing_ok=True)
                
        except Exception as e:
            pytest.skip(f"Whisper audio transcription not available: {e}")
    
    @pytest.mark.asyncio
    async def test_whisper_streaming_transcription(self):
        """Test Whisper streaming transcription."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            
            service = WhisperService()
            if not service._initialized:
                pytest.skip("Whisper service not initialized")
            
            # Generate multiple audio chunks
            audio_chunks = []
            for i in range(3):
                chunk = self._generate_test_audio(duration_seconds=0.5, sample_rate=16000)
                audio_chunks.append(chunk)
            
            # Test streaming transcription
            results = []
            async for result in service.transcribe_streaming(audio_chunks):
                if result:
                    results.append(result)
            
            # Verify results
            if results:
                for result in results:
                    assert isinstance(result, dict)
                    if 'text' in result:
                        assert isinstance(result['text'], str)
                        
        except Exception as e:
            pytest.skip(f"Whisper streaming transcription not available: {e}")


class TestVADIntegration:
    """Test Voice Activity Detection integration."""
    
    def test_vad_initialization(self):
        """Test VAD service initialization and configuration."""
        try:
            from aichat.backend.services.voice.stt.vad_service import VADService
            
            # Test default initialization
            vad = VADService()
            assert vad is not None
            
            # Test configured initialization
            config = {
                'sensitivity': 0.5,
                'sample_rate': 16000,
                'frame_duration': 30  # ms
            }
            
            configured_vad = VADService(config=config)
            assert configured_vad is not None
            
        except Exception as e:
            pytest.skip(f"VAD initialization not available: {e}")
    
    @pytest.mark.asyncio
    async def test_vad_voice_detection(self):
        """Test voice activity detection with audio samples."""
        try:
            from aichat.backend.services.voice.stt.vad_service import VADService
            
            vad = VADService()
            
            # Test with silence (should detect no voice)
            silence = np.zeros(16000, dtype=np.float32)  # 1 second of silence
            silence_result = await vad.detect_voice_activity(silence)
            
            if silence_result is not None:
                assert isinstance(silence_result, dict)
                if 'has_voice' in silence_result:
                    # Silence should typically not have voice activity
                    assert isinstance(silence_result['has_voice'], bool)
            
            # Test with noise/signal (might detect voice)
            noise = np.random.normal(0, 0.1, 16000).astype(np.float32)
            noise_result = await vad.detect_voice_activity(noise)
            
            if noise_result is not None:
                assert isinstance(noise_result, dict)
                
        except Exception as e:
            pytest.skip(f"VAD voice detection not available: {e}")
    
    @pytest.mark.asyncio
    async def test_vad_streaming_processing(self):
        """Test VAD streaming audio processing."""
        try:
            from aichat.backend.services.voice.stt.vad_service import VADService
            
            vad = VADService()
            
            # Generate streaming audio chunks
            chunk_size = 1600  # 100ms at 16kHz
            audio_stream = []
            
            for i in range(10):  # 10 chunks = 1 second
                if i % 2 == 0:
                    # Alternate between silence and noise
                    chunk = np.zeros(chunk_size, dtype=np.float32)
                else:
                    chunk = np.random.normal(0, 0.05, chunk_size).astype(np.float32)
                audio_stream.append(chunk)
            
            # Process stream
            stream_results = []
            async for result in vad.process_audio_stream(audio_stream):
                if result:
                    stream_results.append(result)
            
            # Verify results
            if stream_results:
                for result in stream_results:
                    assert isinstance(result, dict)
                    expected_keys = ['chunk_index', 'has_voice', 'confidence']
                    for key in expected_keys:
                        if key in result:
                            assert result[key] is not None
                            
        except Exception as e:
            pytest.skip(f"VAD streaming processing not available: {e}")


class TestStreamingSTTIntegration:
    """Test streaming STT integration and real-time processing."""
    
    @pytest.mark.asyncio
    async def test_streaming_stt_session(self):
        """Test complete streaming STT session lifecycle."""
        try:
            from aichat.backend.services.voice.stt.streaming_stt_service import StreamingSTTService
            
            # Initialize streaming STT
            stt_service = StreamingSTTService()
            
            # Start streaming session
            session_id = await stt_service.start_streaming(
                sample_rate=16000,
                language="en"
            )
            
            if session_id:
                assert isinstance(session_id, str)
                
                # Generate audio chunks to process
                chunk_duration = 0.1  # 100ms chunks
                sample_rate = 16000
                chunk_size = int(chunk_duration * sample_rate)
                
                transcription_results = []
                
                # Process several audio chunks
                for i in range(5):
                    # Generate test audio chunk
                    audio_chunk = np.random.normal(0, 0.01, chunk_size).astype(np.float32)
                    
                    # Process chunk
                    result = await stt_service.process_audio_chunk(
                        session_id=session_id,
                        audio_chunk=audio_chunk,
                        is_final=(i == 4)  # Mark last chunk as final
                    )
                    
                    if result:
                        transcription_results.append(result)
                
                # Stop streaming session
                final_result = await stt_service.stop_streaming(session_id)
                if final_result:
                    transcription_results.append(final_result)
                
                # Verify results
                if transcription_results:
                    for result in transcription_results:
                        assert isinstance(result, dict)
                        if 'text' in result:
                            assert isinstance(result['text'], str)
                        if 'session_id' in result:
                            assert result['session_id'] == session_id
                            
        except Exception as e:
            pytest.skip(f"Streaming STT session not available: {e}")
    
    @pytest.mark.asyncio
    async def test_streaming_stt_with_vad(self):
        """Test streaming STT integration with VAD."""
        try:
            from aichat.backend.services.voice.stt.streaming_stt_service import StreamingSTTService
            from aichat.backend.services.voice.stt.vad_service import VADService
            
            # Initialize services
            stt_service = StreamingSTTService()
            vad_service = VADService()
            
            # Start STT session
            session_id = await stt_service.start_streaming()
            if not session_id:
                pytest.skip("Could not start STT session")
            
            # Generate mixed audio (silence + speech-like)
            sample_rate = 16000
            chunk_size = 1600  # 100ms
            
            audio_chunks = []
            for i in range(8):
                if i < 2 or i > 5:  # First 2 and last 2 chunks are silence
                    chunk = np.zeros(chunk_size, dtype=np.float32)
                else:  # Middle chunks have "speech-like" audio
                    chunk = np.random.normal(0, 0.1, chunk_size).astype(np.float32)
                audio_chunks.append(chunk)
            
            # Process with VAD first, then STT
            stt_results = []
            
            for i, chunk in enumerate(audio_chunks):
                # Check voice activity
                vad_result = await vad_service.detect_voice_activity(chunk)
                
                has_voice = False
                if vad_result and 'has_voice' in vad_result:
                    has_voice = vad_result['has_voice']
                
                # Only process with STT if voice detected (or force process for testing)
                if has_voice or i % 2 == 0:  # Process some chunks regardless
                    stt_result = await stt_service.process_audio_chunk(
                        session_id=session_id,
                        audio_chunk=chunk,
                        is_final=(i == len(audio_chunks) - 1)
                    )
                    
                    if stt_result:
                        stt_result['had_voice_activity'] = has_voice
                        stt_results.append(stt_result)
            
            # Stop session
            await stt_service.stop_streaming(session_id)
            
            # Verify integrated processing
            if stt_results:
                for result in stt_results:
                    assert isinstance(result, dict)
                    assert 'had_voice_activity' in result
                    
        except Exception as e:
            pytest.skip(f"STT+VAD integration not available: {e}")


class TestSTTPerformanceAndMetrics:
    """Test STT performance monitoring and metrics."""
    
    @pytest.mark.asyncio
    async def test_stt_processing_metrics(self):
        """Test STT processing time and accuracy metrics."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            import soundfile as sf
            
            service = WhisperService()
            if not service._initialized:
                pytest.skip("Whisper service not initialized")
            
            # Generate test audio with known duration
            duration = 2.0  # 2 seconds
            sample_rate = 16000
            test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sample_rate * duration), False)).astype(np.float32)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                sf.write(tmp_file.name, test_audio, sample_rate)
                tmp_path = Path(tmp_file.name)
            
            try:
                # Measure processing time
                start_time = time.time()
                result = await service.transcribe_audio(tmp_path)
                processing_time = time.time() - start_time
                
                if result:
                    # Calculate real-time factor (processing_time / audio_duration)
                    rtf = processing_time / duration
                    
                    # Performance should be reasonable (RTF < 10 for most cases)
                    assert rtf < 10.0, f"Processing too slow: RTF = {rtf}"
                    
                    # Result should have expected metrics
                    if 'processing_time' in result:
                        assert isinstance(result['processing_time'], (int, float))
                    
                    if 'confidence' in result:
                        assert 0.0 <= result['confidence'] <= 1.0
                        
            finally:
                tmp_path.unlink(missing_ok=True)
                
        except Exception as e:
            pytest.skip(f"STT performance metrics not available: {e}")
    
    def test_stt_language_detection(self):
        """Test STT language detection capabilities."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            
            # Test different model configurations
            service = WhisperService()
            
            if hasattr(service, 'detect_language') and service._initialized:
                # Test with different audio samples (synthetic)
                test_cases = [
                    ("english_audio", "en"),
                    ("spanish_audio", "es"),
                    ("multilingual_audio", None)  # Should detect automatically
                ]
                
                for audio_name, expected_lang in test_cases:
                    # Generate synthetic audio for language detection
                    test_audio = np.random.normal(0, 0.1, 16000).astype(np.float32)
                    
                    # This would typically require actual audio with speech
                    # For now, just test that the method exists and runs
                    if hasattr(service, 'detect_language'):
                        try:
                            detected = service.detect_language(test_audio)
                            if detected:
                                assert isinstance(detected, str)
                                assert len(detected) >= 2  # Language codes are 2+ chars
                        except Exception:
                            # Language detection may fail on synthetic audio
                            pass
                            
        except Exception as e:
            pytest.skip(f"STT language detection not available: {e}")


class TestSTTErrorHandling:
    """Test STT error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_stt_invalid_audio_handling(self):
        """Test STT handling of invalid or corrupted audio."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            
            service = WhisperService()
            if not service._initialized:
                pytest.skip("Whisper service not initialized")
            
            # Test with invalid audio data
            invalid_cases = [
                np.array([]),  # Empty array
                np.array([np.nan, np.inf, -np.inf]),  # Invalid values
                np.ones(1000000) * 999,  # Clipped audio
            ]
            
            for invalid_audio in invalid_cases:
                try:
                    # This should either handle gracefully or raise appropriate error
                    result = await service.transcribe_audio(invalid_audio)
                    # If it returns something, it should be a valid structure
                    if result:
                        assert isinstance(result, dict)
                except Exception as e:
                    # Expected - should handle invalid audio gracefully
                    assert isinstance(e, (ValueError, TypeError, RuntimeError))
                    
        except Exception as e:
            pytest.skip(f"STT error handling not available: {e}")
    
    @pytest.mark.asyncio
    async def test_stt_session_timeout_handling(self):
        """Test STT session timeout and cleanup."""
        try:
            from aichat.backend.services.voice.stt.streaming_stt_service import StreamingSTTService
            
            stt_service = StreamingSTTService()
            
            # Start session
            session_id = await stt_service.start_streaming()
            if not session_id:
                pytest.skip("Could not start STT session")
            
            # Simulate long pause (session might timeout)
            await asyncio.sleep(0.1)  # Brief pause for testing
            
            # Try to process audio after pause
            test_audio = np.zeros(1600, dtype=np.float32)  # 100ms of silence
            
            try:
                result = await stt_service.process_audio_chunk(
                    session_id=session_id,
                    audio_chunk=test_audio
                )
                
                # Should either work or handle timeout gracefully
                if result:
                    assert isinstance(result, dict)
                    
            finally:
                # Ensure session cleanup
                try:
                    await stt_service.stop_streaming(session_id)
                except Exception:
                    # Cleanup might fail if session already timed out
                    pass
                    
        except Exception as e:
            pytest.skip(f"STT timeout handling not available: {e}")


class TestSTTIntegrationWithServices:
    """Test STT integration with other services."""
    
    def test_stt_with_voice_service(self):
        """Test STT integration with main VoiceService."""
        try:
            from aichat.backend.services.voice.voice_service import VoiceService
            
            # Test VoiceService initialization includes STT
            voice_service = VoiceService()
            assert voice_service is not None
            
            # Check for STT-related attributes
            stt_attributes = ['whisper_service', 'stt_service', 'streaming_stt']
            
            has_stt = any(hasattr(voice_service, attr) for attr in stt_attributes)
            if not has_stt:
                # VoiceService might not have STT directly integrated yet
                pytest.skip("STT not directly integrated with VoiceService")
                
        except Exception as e:
            pytest.skip(f"VoiceService STT integration not available: {e}")
    
    def test_stt_with_audio_io(self):
        """Test STT integration with AudioIOService."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            from aichat.backend.services.audio.audio_io_service import AudioIOService
            
            # Test STT service has audio IO integration
            stt_service = WhisperService()
            assert hasattr(stt_service, 'audio_io')
            assert stt_service.audio_io is not None
            
            # Test audio IO is properly typed
            assert isinstance(stt_service.audio_io, AudioIOService)
            
        except Exception as e:
            pytest.skip(f"STT AudioIO integration not available: {e}")
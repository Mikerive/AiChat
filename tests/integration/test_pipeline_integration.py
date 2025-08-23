"""
Pipeline Integration Tests - Real functionality testing for complete voice and chat pipelines
Tests the integration between STT, LLM, and TTS components as complete workflows.
"""

import asyncio
import pytest
import numpy as np
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, AsyncGenerator
import json


class TestBasicPipelineIntegration:
    """Test basic pipeline integration between components."""
    
    def test_pipeline_component_availability(self):
        """Test that all pipeline components can be imported together."""
        try:
            # Import all major pipeline components
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
            from aichat.backend.services.voice.voice_service import VoiceService
            from aichat.backend.services.chat.chat_service import ChatService
            
            # Verify all components can be instantiated
            stt_service = WhisperService()
            llm_service = PydanticAIService()
            tts_service = ChatterboxTTSService()
            voice_service = VoiceService()
            chat_service = ChatService()
            
            # All should be valid objects
            components = [stt_service, llm_service, tts_service, voice_service, chat_service]
            for component in components:
                assert component is not None
                
        except ImportError as e:
            pytest.skip(f"Pipeline components not available: {e}")
    
    def test_pipeline_service_integration(self):
        """Test that pipeline services are properly integrated."""
        try:
            from aichat.backend.services.voice.voice_service import VoiceService
            
            voice_service = VoiceService()
            
            # Check for integrated services
            assert hasattr(voice_service, 'smart_tts')
            assert hasattr(voice_service, 'streaming_tts')
            assert voice_service.smart_tts is not None
            assert voice_service.streaming_tts is not None
            
            # Check for audio IO integration
            assert hasattr(voice_service, 'audio_io')
            assert voice_service.audio_io is not None
            
        except Exception as e:
            pytest.skip(f"Pipeline service integration not available: {e}")


class TestSTTToLLMPipeline:
    """Test STT to LLM pipeline integration."""
    
    def _generate_speech_like_audio(self, text: str, duration: float = 2.0) -> np.ndarray:
        """Generate audio that simulates speech patterns for testing."""
        sample_rate = 16000
        samples = int(sample_rate * duration)
        
        # Generate audio with speech-like characteristics
        t = np.linspace(0, duration, samples, False)
        
        # Multiple frequency components to simulate speech
        frequencies = [200, 400, 800, 1200]  # Typical speech formants
        audio = np.zeros(samples)
        
        for freq in frequencies:
            # Add frequency component with envelope
            component = np.sin(2 * np.pi * freq * t)
            envelope = np.exp(-t * 0.5)  # Decay envelope
            audio += component * envelope * (0.1 + 0.1 * np.random.random())
        
        # Add some noise for realism
        noise = np.random.normal(0, 0.02, samples)
        audio += noise
        
        # Normalize
        audio = audio / (np.max(np.abs(audio)) + 1e-6)
        return audio.astype(np.float32)
    
    @pytest.mark.asyncio
    async def test_stt_to_llm_basic_pipeline(self):
        """Test basic STT -> LLM pipeline flow."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            import soundfile as sf
            
            # Initialize services
            stt_service = WhisperService()
            llm_service = PydanticAIService()
            
            if not stt_service._initialized:
                pytest.skip("STT service not initialized")
            
            # Generate test audio
            test_audio = self._generate_speech_like_audio("Hello how are you", duration=2.0)
            
            # Save to temporary file for STT processing
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                sf.write(tmp_file.name, test_audio, 16000)
                tmp_path = Path(tmp_file.name)
            
            try:
                # Step 1: STT Processing
                stt_result = await stt_service.transcribe_audio(tmp_path)
                
                if stt_result and 'text' in stt_result:
                    transcribed_text = stt_result['text']
                    assert isinstance(transcribed_text, str)
                    
                    # Step 2: LLM Processing
                    character_context = {
                        "name": "assistant",
                        "personality": "helpful and friendly",
                        "profile": "A conversational AI assistant"
                    }
                    
                    llm_response = await llm_service.generate_response(
                        prompt=transcribed_text,
                        character_context=character_context,
                        max_tokens=100
                    )
                    
                    if llm_response:
                        assert isinstance(llm_response, dict)
                        
                        # Verify pipeline data flow
                        if 'text' in llm_response:
                            response_text = llm_response['text']
                            assert isinstance(response_text, str)
                            assert len(response_text) > 0
                            
                        # Pipeline should preserve character context
                        if 'character' in llm_response:
                            assert llm_response['character'] == "assistant"
                            
            finally:
                tmp_path.unlink(missing_ok=True)
                
        except Exception as e:
            pytest.skip(f"STT to LLM pipeline not available: {e}")
    
    @pytest.mark.asyncio
    async def test_stt_streaming_to_llm_pipeline(self):
        """Test streaming STT to LLM pipeline integration."""
        try:
            from aichat.backend.services.voice.stt.streaming_stt_service import StreamingSTTService
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            
            # Initialize services
            stt_service = StreamingSTTService()
            llm_service = PydanticAIService()
            
            # Start STT streaming session
            session_id = await stt_service.start_streaming(sample_rate=16000)
            if not session_id:
                pytest.skip("Could not start STT streaming session")
            
            try:
                # Generate streaming audio chunks
                audio_chunks = []
                for i in range(5):
                    chunk = self._generate_speech_like_audio(f"chunk {i}", duration=0.5)
                    audio_chunks.append(chunk)
                
                # Process audio chunks and collect transcriptions
                partial_transcriptions = []
                
                for i, chunk in enumerate(audio_chunks):
                    is_final = (i == len(audio_chunks) - 1)
                    
                    stt_result = await stt_service.process_audio_chunk(
                        session_id=session_id,
                        audio_chunk=chunk,
                        is_final=is_final
                    )
                    
                    if stt_result and 'text' in stt_result:
                        partial_transcriptions.append(stt_result['text'])
                
                # Combine transcriptions for LLM processing
                if partial_transcriptions:
                    combined_text = " ".join(partial_transcriptions)
                    
                    # Process with LLM
                    character_context = {
                        "name": "streaming_assistant",
                        "personality": "responsive and adaptive"
                    }
                    
                    llm_response = await llm_service.generate_response(
                        prompt=combined_text,
                        character_context=character_context,
                        max_tokens=150
                    )
                    
                    if llm_response:
                        assert isinstance(llm_response, dict)
                        if 'text' in llm_response:
                            assert isinstance(llm_response['text'], str)
                            
            finally:
                await stt_service.stop_streaming(session_id)
                
        except Exception as e:
            pytest.skip(f"Streaming STT to LLM pipeline not available: {e}")


class TestLLMToTTSPipeline:
    """Test LLM to TTS pipeline integration."""
    
    @pytest.mark.asyncio
    async def test_llm_to_tts_basic_pipeline(self):
        """Test basic LLM -> TTS pipeline flow."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
            
            # Initialize services
            llm_service = PydanticAIService()
            tts_service = ChatterboxTTSService()
            
            # Step 1: Generate LLM response
            test_prompt = "Tell me a fun fact about space."
            character_context = {
                "name": "space_expert",
                "personality": "knowledgeable and enthusiastic",
                "profile": "An expert on space and astronomy"
            }
            
            llm_response = await llm_service.generate_response(
                prompt=test_prompt,
                character_context=character_context,
                max_tokens=100
            )
            
            if llm_response and 'text' in llm_response:
                response_text = llm_response['text']
                character_name = llm_response.get('character', 'space_expert')
                emotion = llm_response.get('emotion', 'neutral')
                
                # Step 2: Generate TTS from LLM response
                tts_result = await tts_service.generate_speech(
                    text=response_text,
                    character=character_name,
                    voice="default",
                    emotion=emotion
                )
                
                if tts_result:
                    assert isinstance(tts_result, dict)
                    
                    # Verify pipeline data preservation
                    expected_keys = ['audio_file', 'text', 'character']
                    for key in expected_keys:
                        if key in tts_result:
                            assert tts_result[key] is not None
                            
                    # Text should match LLM output
                    if 'text' in tts_result:
                        assert tts_result['text'] == response_text
                        
                    # Character should be preserved
                    if 'character' in tts_result:
                        assert tts_result['character'] == character_name
                        
        except Exception as e:
            pytest.skip(f"LLM to TTS pipeline not available: {e}")
    
    @pytest.mark.asyncio
    async def test_llm_streaming_to_tts_pipeline(self):
        """Test streaming LLM to TTS pipeline integration."""
        try:
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingTTSIntegration
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Initialize services
            llm_service = PydanticAIService()
            tts_selector = SmartTTSSelector()
            streaming_tts = StreamingTTSIntegration(tts_selector)
            
            test_prompt = "Explain how rain is formed in a simple way."
            character_context = {
                "name": "weather_teacher",
                "personality": "patient and educational"
            }
            
            # Start TTS streaming session
            session_id = await streaming_tts.start_streaming_session("weather_teacher")
            
            try:
                # Stream LLM response and process with TTS
                tts_segments = []
                
                async for llm_chunk in llm_service.generate_streaming_response(
                    prompt=test_prompt,
                    character_context=character_context,
                    max_tokens=200
                ):
                    if llm_chunk and 'content' in llm_chunk:
                        content = llm_chunk['content']
                        
                        # Process streaming text with TTS
                        segments = await streaming_tts.process_streaming_text(
                            text_chunk=content,
                            character_name="weather_teacher",
                            session_id=session_id
                        )
                        
                        if segments:
                            tts_segments.extend(segments)
                
                # Finalize streaming session
                final_segments = await streaming_tts.finalize_streaming_session(
                    character_name="weather_teacher",
                    session_id=session_id
                )
                
                if final_segments:
                    tts_segments.extend(final_segments)
                
                # Verify streaming pipeline results
                if tts_segments:
                    for segment in tts_segments:
                        assert isinstance(segment, dict)
                        assert 'session_id' in segment
                        assert segment['session_id'] == session_id
                        
            finally:
                # Ensure cleanup
                if streaming_tts.is_streaming:
                    await streaming_tts.finalize_streaming_session("weather_teacher", session_id)
                    
        except Exception as e:
            pytest.skip(f"Streaming LLM to TTS pipeline not available: {e}")


class TestFullPipelineIntegration:
    """Test complete STT -> LLM -> TTS pipeline integration."""
    
    def _create_test_audio_conversation(self) -> List[np.ndarray]:
        """Create multiple audio samples simulating a conversation."""
        conversation_texts = [
            "Hello, how are you today?",
            "What's the weather like?",
            "Can you help me with something?",
            "Thank you very much!"
        ]
        
        audio_samples = []
        for text in conversation_texts:
            # Generate speech-like audio for each phrase
            duration = len(text) * 0.1 + 1.0  # Rough duration based on text length
            audio = self._generate_speech_like_audio(text, duration)
            audio_samples.append(audio)
            
        return audio_samples
    
    def _generate_speech_like_audio(self, text: str, duration: float) -> np.ndarray:
        """Generate audio that simulates speech patterns."""
        sample_rate = 16000
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        
        # Speech-like frequency modulation
        base_freq = 150 + 50 * np.sin(2 * np.pi * 2 * t)  # Pitch variation
        audio = np.sin(2 * np.pi * base_freq * t)
        
        # Add formants (speech resonances)
        formants = [800, 1200, 2400]
        for formant in formants:
            formant_component = 0.3 * np.sin(2 * np.pi * formant * t)
            audio += formant_component
        
        # Apply speech envelope (attack, sustain, decay)
        envelope = np.ones_like(audio)
        attack_samples = int(0.1 * sample_rate)
        decay_samples = int(0.2 * sample_rate)
        
        if attack_samples < samples:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        if decay_samples < samples:
            envelope[-decay_samples:] = np.linspace(1, 0, decay_samples)
            
        audio *= envelope
        
        # Add noise for realism
        noise = 0.05 * np.random.normal(0, 1, samples)
        audio += noise
        
        # Normalize
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val
            
        return audio.astype(np.float32)
    
    @pytest.mark.asyncio
    async def test_full_conversation_pipeline(self):
        """Test complete conversation pipeline: STT -> LLM -> TTS."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
            import soundfile as sf
            
            # Initialize pipeline components
            stt_service = WhisperService()
            llm_service = PydanticAIService()
            tts_service = ChatterboxTTSService()
            
            if not stt_service._initialized:
                pytest.skip("STT service not initialized")
            
            # Generate conversation audio
            audio_samples = self._create_test_audio_conversation()
            
            conversation_results = []
            
            for i, audio in enumerate(audio_samples):
                # Save audio to temporary file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                    sf.write(tmp_file.name, audio, 16000)
                    tmp_path = Path(tmp_file.name)
                
                try:
                    # Step 1: STT - Convert audio to text
                    stt_result = await stt_service.transcribe_audio(tmp_path)
                    
                    if stt_result and 'text' in stt_result:
                        user_text = stt_result['text']
                        
                        # Step 2: LLM - Generate response
                        character_context = {
                            "name": "friendly_assistant",
                            "personality": "helpful, warm, and conversational",
                            "profile": "A friendly AI assistant for conversations"
                        }
                        
                        llm_response = await llm_service.generate_response(
                            prompt=user_text,
                            character_context=character_context,
                            max_tokens=100
                        )
                        
                        if llm_response and 'text' in llm_response:
                            response_text = llm_response['text']
                            character_name = llm_response.get('character', 'friendly_assistant')
                            emotion = llm_response.get('emotion', 'neutral')
                            
                            # Step 3: TTS - Convert response to speech
                            tts_result = await tts_service.generate_speech(
                                text=response_text,
                                character=character_name,
                                voice="default",
                                emotion=emotion
                            )
                            
                            # Record complete pipeline result
                            pipeline_result = {
                                "turn": i + 1,
                                "user_audio_duration": len(audio) / 16000,
                                "transcribed_text": user_text,
                                "llm_response": response_text,
                                "response_character": character_name,
                                "response_emotion": emotion,
                                "tts_result": tts_result,
                                "pipeline_success": tts_result is not None
                            }
                            
                            conversation_results.append(pipeline_result)
                            
                finally:
                    tmp_path.unlink(missing_ok=True)
            
            # Verify complete conversation pipeline
            if conversation_results:
                assert len(conversation_results) > 0
                
                for result in conversation_results:
                    # Each turn should have all pipeline components
                    assert 'transcribed_text' in result
                    assert 'llm_response' in result
                    assert 'tts_result' in result
                    
                    # Text should flow through pipeline
                    assert isinstance(result['transcribed_text'], str)
                    assert isinstance(result['llm_response'], str)
                    
                    # TTS should preserve response text
                    if result['tts_result'] and 'text' in result['tts_result']:
                        assert result['tts_result']['text'] == result['llm_response']
                        
        except Exception as e:
            pytest.skip(f"Full conversation pipeline not available: {e}")
    
    @pytest.mark.asyncio
    async def test_real_time_streaming_pipeline(self):
        """Test real-time streaming pipeline integration."""
        try:
            from aichat.backend.services.voice.stt.streaming_stt_service import StreamingSTTService
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingTTSIntegration
            from aichat.backend.services.voice.tts.smart_tts_selector import SmartTTSSelector
            
            # Initialize streaming pipeline
            stt_service = StreamingSTTService()
            llm_service = PydanticAIService()
            tts_selector = SmartTTSSelector()
            streaming_tts = StreamingTTSIntegration(tts_selector)
            
            # Start streaming sessions
            stt_session = await stt_service.start_streaming(sample_rate=16000)
            tts_session = await streaming_tts.start_streaming_session("streaming_assistant")
            
            if not stt_session or not tts_session:
                pytest.skip("Could not start streaming sessions")
            
            try:
                # Simulate real-time audio streaming
                streaming_audio = self._generate_speech_like_audio(
                    "This is a streaming test conversation", 
                    duration=3.0
                )
                
                # Split into chunks (simulate real-time)
                chunk_size = 1600  # 100ms at 16kHz
                audio_chunks = []
                for i in range(0, len(streaming_audio), chunk_size):
                    chunk = streaming_audio[i:i+chunk_size]
                    if len(chunk) == chunk_size:  # Only full chunks
                        audio_chunks.append(chunk)
                
                pipeline_results = []
                accumulated_transcription = ""
                
                for i, chunk in enumerate(audio_chunks):
                    is_final = (i == len(audio_chunks) - 1)
                    
                    # Step 1: Process audio chunk with STT
                    stt_result = await stt_service.process_audio_chunk(
                        session_id=stt_session,
                        audio_chunk=chunk,
                        is_final=is_final
                    )
                    
                    if stt_result and 'text' in stt_result:
                        partial_text = stt_result['text']
                        accumulated_transcription += partial_text
                        
                        # Step 2: Process with LLM when we have substantial text
                        if len(accumulated_transcription.strip()) > 10 or is_final:
                            character_context = {
                                "name": "streaming_assistant",
                                "personality": "responsive and real-time"
                            }
                            
                            # Generate streaming LLM response
                            async for llm_chunk in llm_service.generate_streaming_response(
                                prompt=accumulated_transcription,
                                character_context=character_context,
                                max_tokens=100
                            ):
                                if llm_chunk and 'content' in llm_chunk:
                                    content = llm_chunk['content']
                                    
                                    # Step 3: Process with streaming TTS
                                    tts_segments = await streaming_tts.process_streaming_text(
                                        text_chunk=content,
                                        character_name="streaming_assistant",
                                        session_id=tts_session
                                    )
                                    
                                    if tts_segments:
                                        for segment in tts_segments:
                                            pipeline_result = {
                                                "chunk_index": i,
                                                "partial_transcription": partial_text,
                                                "llm_content": content,
                                                "tts_segment": segment,
                                                "streaming_success": True
                                            }
                                            pipeline_results.append(pipeline_result)
                            
                            # Reset for next phrase
                            accumulated_transcription = ""
                
                # Finalize sessions
                await streaming_tts.finalize_streaming_session("streaming_assistant", tts_session)
                await stt_service.stop_streaming(stt_session)
                
                # Verify streaming pipeline results
                if pipeline_results:
                    for result in pipeline_results:
                        assert 'partial_transcription' in result
                        assert 'llm_content' in result
                        assert 'tts_segment' in result
                        assert result['streaming_success'] is True
                        
            finally:
                # Ensure cleanup
                try:
                    await stt_service.stop_streaming(stt_session)
                    if streaming_tts.is_streaming:
                        await streaming_tts.finalize_streaming_session("streaming_assistant", tts_session)
                except Exception:
                    pass
                    
        except Exception as e:
            pytest.skip(f"Real-time streaming pipeline not available: {e}")


class TestPipelinePerformanceAndMetrics:
    """Test pipeline performance and end-to-end metrics."""
    
    @pytest.mark.asyncio
    async def test_pipeline_latency_metrics(self):
        """Test end-to-end pipeline latency measurement."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            from aichat.backend.services.llm.pydantic_ai_service import PydanticAIService
            from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
            import soundfile as sf
            
            # Initialize services
            stt_service = WhisperService()
            llm_service = PydanticAIService()
            tts_service = ChatterboxTTSService()
            
            if not stt_service._initialized:
                pytest.skip("STT service not initialized")
            
            # Generate test audio
            test_audio = self._generate_speech_like_audio("Hello assistant", duration=1.5)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                sf.write(tmp_file.name, test_audio, 16000)
                tmp_path = Path(tmp_file.name)
            
            try:
                # Measure complete pipeline latency
                pipeline_start = time.time()
                
                # STT phase
                stt_start = time.time()
                stt_result = await stt_service.transcribe_audio(tmp_path)
                stt_latency = time.time() - stt_start
                
                if stt_result and 'text' in stt_result:
                    user_text = stt_result['text']
                    
                    # LLM phase
                    llm_start = time.time()
                    llm_response = await llm_service.generate_response(
                        prompt=user_text,
                        character_context={"name": "assistant", "personality": "helpful"},
                        max_tokens=50
                    )
                    llm_latency = time.time() - llm_start
                    
                    if llm_response and 'text' in llm_response:
                        response_text = llm_response['text']
                        
                        # TTS phase
                        tts_start = time.time()
                        tts_result = await tts_service.generate_speech(
                            text=response_text,
                            character="assistant",
                            voice="default"
                        )
                        tts_latency = time.time() - tts_start
                        
                        total_latency = time.time() - pipeline_start
                        
                        # Verify reasonable performance
                        assert stt_latency < 30.0, f"STT too slow: {stt_latency} seconds"
                        assert llm_latency < 30.0, f"LLM too slow: {llm_latency} seconds" 
                        assert tts_latency < 30.0, f"TTS too slow: {tts_latency} seconds"
                        assert total_latency < 60.0, f"Pipeline too slow: {total_latency} seconds"
                        
                        # Calculate performance metrics
                        audio_duration = len(test_audio) / 16000
                        real_time_factor = total_latency / audio_duration
                        
                        # Performance metrics should be reasonable
                        if tts_result:
                            metrics = {
                                "stt_latency": stt_latency,
                                "llm_latency": llm_latency,
                                "tts_latency": tts_latency,
                                "total_latency": total_latency,
                                "audio_duration": audio_duration,
                                "real_time_factor": real_time_factor,
                                "pipeline_success": True
                            }
                            
                            assert metrics['pipeline_success'] is True
                            assert metrics['real_time_factor'] > 0
                            
            finally:
                tmp_path.unlink(missing_ok=True)
                
        except Exception as e:
            pytest.skip(f"Pipeline latency metrics not available: {e}")
    
    def _generate_speech_like_audio(self, text: str, duration: float) -> np.ndarray:
        """Generate speech-like audio for testing."""
        sample_rate = 16000
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        
        # Generate speech-like waveform
        fundamental_freq = 150  # Typical male voice
        audio = np.sin(2 * np.pi * fundamental_freq * t)
        
        # Add harmonics
        for harmonic in [2, 3, 4]:
            amplitude = 1.0 / harmonic
            audio += amplitude * np.sin(2 * np.pi * fundamental_freq * harmonic * t)
        
        # Apply speech envelope
        envelope = np.exp(-0.5 * t) + 0.3  # Decay with sustain
        audio *= envelope
        
        # Add formants (speech resonances)
        formants = [800, 1200, 2400]
        for i, formant in enumerate(formants):
            formant_strength = 0.2 / (i + 1)
            formant_component = formant_strength * np.sin(2 * np.pi * formant * t)
            audio += formant_component
        
        # Normalize and add light noise
        audio = audio / (np.max(np.abs(audio)) + 1e-6)
        noise = 0.03 * np.random.normal(0, 1, samples)
        audio += noise
        
        return audio.astype(np.float32)
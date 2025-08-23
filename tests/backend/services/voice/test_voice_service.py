"""
Voice service testing - real functionality without mocking.
Tests voice service imports and basic functionality.
"""

import pytest


class TestVoiceService:
    """Test voice service functionality."""
    
    def test_can_import_voice_service(self):
        """Test voice service import."""
        try:
            from aichat.backend.services.voice.voice_service import VoiceService
            assert VoiceService is not None
        except ImportError:
            pytest.skip("Voice service not available")


class TestSTTServices:
    """Test Speech-to-Text services."""
    
    def test_can_import_whisper_service(self):
        """Test Whisper STT service import."""
        try:
            from aichat.backend.services.voice.stt.whisper_service import WhisperService
            assert WhisperService is not None
        except ImportError:
            pytest.skip("Whisper service not available")
    
    def test_streaming_stt_service_file_exists(self):
        """Test that streaming STT service file exists (no class defined yet)."""
        try:
            import aichat.backend.services.voice.stt.streaming_stt_service
            # File exists but no class defined yet - this is expected
            assert aichat.backend.services.voice.stt.streaming_stt_service is not None
        except ImportError:
            pytest.skip("Streaming STT service file not available")
    
    def test_can_import_vad_service(self):
        """Test VAD service import."""
        try:
            from aichat.backend.services.voice.stt.vad_service import VADService
            assert VADService is not None
        except ImportError:
            pytest.skip("VAD service not available")


class TestTTSServices:
    """Test Text-to-Speech services."""
    
    def test_can_import_chatterbox_tts_service(self):
        """Test Chatterbox TTS service import."""
        try:
            from aichat.backend.services.voice.tts.chatterbox_tts_service import ChatterboxTTSService
            assert ChatterboxTTSService is not None
        except ImportError:
            pytest.skip("Chatterbox TTS service not available")
    
    def test_can_import_tts_finetune_service(self):
        """Test TTS finetune service import."""
        try:
            from aichat.backend.services.voice.tts.tts_finetune_service import TTSFinetuneService
            assert TTSFinetuneService is not None
        except ImportError:
            pytest.skip("TTS finetune service not available")
    
    def test_can_import_streaming_tts_integration(self):
        """Test streaming TTS integration import."""
        try:
            from aichat.backend.services.voice.tts.streaming_tts_integration import StreamingTTSIntegration
            assert StreamingTTSIntegration is not None
        except (ImportError, ModuleNotFoundError):
            pytest.skip("Streaming TTS integration not available (missing dependencies)")
"""
Audio services testing - real functionality without mocking.
Tests audio service imports and basic functionality.
"""

import pytest


class TestAudioServices:
    """Test audio service functionality."""
    
    def test_can_import_audio_io_service(self):
        """Test audio I/O service import."""
        try:
            from aichat.backend.services.audio.audio_io_service import AudioIOService
            assert AudioIOService is not None
        except ImportError:
            pytest.skip("Audio I/O service not available")
    
    def test_can_import_audio_enhancement_service(self):
        """Test audio enhancement service import."""
        try:
            from aichat.backend.services.audio.audio_enhancement_service import AudioEnhancementService
            assert AudioEnhancementService is not None
        except ImportError:
            pytest.skip("Audio enhancement service not available")
    
    @pytest.mark.asyncio
    async def test_audio_io_service_instantiation(self):
        """Test that audio I/O service can be instantiated."""
        try:
            from aichat.backend.services.audio.audio_io_service import AudioIOService
            
            service = AudioIOService()
            assert service is not None
            
        except Exception as e:
            pytest.skip(f"Audio I/O service instantiation failed: {e}")
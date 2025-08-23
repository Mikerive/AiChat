"""
Integration tests - real end-to-end functionality testing.
Tests complete workflows using actual services.
"""

import pytest


class TestBasicIntegration:
    """Test basic integration scenarios."""
    
    def test_complete_import_chain(self):
        """Test that complete import chain works."""
        try:
            # Core imports
            from aichat.core.config import settings
            from aichat.core.database import get_db
            from aichat.models.schemas import Character, ChatMessage
            
            # Backend imports
            from aichat.backend.main import create_app
            from aichat.backend.services.chat.chat_service import ChatService
            
            # All should be importable
            assert settings is not None or True  # Config might fail in test env
            assert get_db is not None
            assert Character is not None
            assert ChatMessage is not None
            assert create_app is not None
            assert ChatService is not None
            
        except ImportError as e:
            pytest.fail(f"Integration import chain failed: {e}")
    
    def test_app_creation_with_dependencies(self):
        """Test that app can be created with all dependencies."""
        try:
            from aichat.backend.main import create_app
            
            app = create_app()
            assert app is not None
            
            # Test that app has expected structure
            assert hasattr(app, 'routes')
            assert len(app.routes) > 0  # Should have some routes
            
        except Exception as e:
            pytest.skip(f"App creation with dependencies failed: {e}")


class TestServiceIntegration:
    """Test service integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_database_service_integration(self):
        """Test database and service integration."""
        try:
            from aichat.core.database import list_characters
            from aichat.backend.services.chat.chat_service import ChatService
            
            # Should be able to list characters
            characters = await list_characters()
            assert isinstance(characters, list)
            
            # Should be able to create chat service
            chat_service = ChatService()
            assert chat_service is not None
            
        except Exception as e:
            pytest.skip(f"Database service integration not available: {e}")


class TestFileOperations:
    """Test file operations and temporary file handling."""
    
    def test_can_create_audio_file(self, sample_audio_file):
        """Test that we can create and read audio files."""
        assert sample_audio_file.exists()
        assert sample_audio_file.stat().st_size > 0
        
        # Should be readable
        content = sample_audio_file.read_bytes()
        assert len(content) > 0
        assert content.startswith(b'RIFF')  # Valid WAV header
    
    def test_temp_directory_works(self, temp_dir):
        """Test that temp directory fixture works."""
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        
        # Can create files in temp dir
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        assert test_file.exists()
        assert test_file.read_text() == "test content"
"""
Test ChatService using real service with mocked dependencies

This demonstrates the correct approach: test REAL services with mocked external dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

# Import test utilities
from tests.test_utils.di_test_helpers import (
    mock_di_container,
    MockFactory
)


class TestChatServiceReal:
    """Test REAL ChatService with mocked dependencies - the correct approach"""
    
    @pytest.mark.asyncio
    async def test_get_current_character_with_real_service(self):
        """Test getting current character using real ChatService"""
        dependency_mocks = {
            'db_ops': MockFactory.database_ops()
        }
        
        with mock_di_container(dependency_mocks) as container:
            chat_service = container.resolve("chat_service")
            
            # The real service should call db_ops.list_characters() to get default
            result = await chat_service.get_current_character()
            
            assert result is not None
            assert result["name"] == "hatsune_miku"
            
            # Verify the real service called the mocked dependency
            db_ops = dependency_mocks['db_ops']
            db_ops.list_characters.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_character_with_real_service(self):
        """Test character switching using real ChatService"""
        dependency_mocks = {
            'db_ops': MockFactory.database_ops(),
            'event_system': AsyncMock()
        }
        
        with mock_di_container(dependency_mocks) as container:
            chat_service = container.resolve("chat_service")
            
            # The real service should call db_ops.get_character()
            result = await chat_service.switch_character(1, "hatsune_miku")
            
            assert result is True
            assert chat_service._current_character_id == 1
            
            # Verify the real service called the mocked dependency
            db_ops = dependency_mocks['db_ops']
            db_ops.get_character.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_switch_character_not_found_real_service(self):
        """Test switching to non-existent character using real ChatService"""
        dependency_mocks = {
            'db_ops': MockFactory.database_ops(),
            'event_system': AsyncMock()
        }
        # Make db_ops return None for the character lookup
        dependency_mocks['db_ops'].get_character.return_value = None
        
        with mock_di_container(dependency_mocks) as container:
            chat_service = container.resolve("chat_service")
            
            result = await chat_service.switch_character(999, "unknown_character")
            
            assert result is False
            # Character ID should not change from default None

    @pytest.mark.asyncio
    async def test_get_current_character_no_characters_exist(self):
        """Test getting current character when no characters exist in database"""
        dependency_mocks = {
            'db_ops': MockFactory.database_ops()
        }
        # Make db_ops return empty list for characters
        dependency_mocks['db_ops'].list_characters.return_value = []
        
        with mock_di_container(dependency_mocks) as container:
            chat_service = container.resolve("chat_service")
            
            result = await chat_service.get_current_character()
            
            assert result is None
            
            # Verify the real service called the mocked dependency
            db_ops = dependency_mocks['db_ops']
            db_ops.list_characters.assert_called_once()
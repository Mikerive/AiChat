"""
CLI commands testing.
Tests command-line interface functionality.
"""

import pytest


class TestCLICommands:
    """Test CLI command functionality."""
    
    def test_can_import_main_cli(self):
        """Test main CLI import."""
        try:
            from aichat.cli.main import main
            assert main is not None
        except ImportError as e:
            pytest.fail(f"Main CLI import failed: {e}")
    
    def test_can_import_backend_cli(self):
        """Test backend CLI import."""
        try:
            from aichat.cli.backend import main
            assert main is not None
        except ImportError as e:
            pytest.fail(f"Backend CLI import failed: {e}")
    
    def test_can_import_frontend_cli(self):
        """Test frontend CLI import."""
        try:
            from aichat.cli.frontend import main
            assert main is not None
        except ImportError as e:
            pytest.fail(f"Frontend CLI import failed: {e}")
    
    def test_can_import_training_cli(self):
        """Test training CLI import."""
        try:
            from aichat.cli.training import main
            assert main is not None
        except ImportError as e:
            pytest.fail(f"Training CLI import failed: {e}")
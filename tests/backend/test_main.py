"""
Backend main application testing.
Tests FastAPI app creation and basic functionality.
"""

import pytest


class TestBackendMain:
    """Test backend main application."""
    
    def test_can_import_create_app(self):
        """Test that create_app can be imported."""
        try:
            from aichat.backend.main import create_app
            assert create_app is not None
        except ImportError as e:
            pytest.fail(f"Backend main import failed: {e}")
    
    def test_can_create_app(self):
        """Test that FastAPI app can be created."""
        try:
            from aichat.backend.main import create_app
            
            app = create_app()
            assert app is not None
            assert hasattr(app, 'openapi')  # FastAPI app should have openapi method
            
        except Exception as e:
            pytest.fail(f"App creation failed: {e}")
    
    def test_app_has_required_routes(self):
        """Test that app has required route prefixes."""
        try:
            from aichat.backend.main import create_app
            
            app = create_app()
            
            # Get routes from the app
            routes = [route.path for route in app.routes]
            
            # Check that we have the main route patterns
            has_root = any('/' == route for route in routes)
            has_health = any('/health' in route for route in routes)
            
            assert has_root or has_health, "App should have basic routes"
            
        except Exception as e:
            pytest.fail(f"Route validation failed: {e}")
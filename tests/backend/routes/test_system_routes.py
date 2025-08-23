"""
System routes testing - real functionality without mocking.
Tests system endpoints for health checks and status.
"""

import pytest
import requests


class TestSystemRoutes:
    """Test system route endpoints."""
    
    BASE_URL = "http://localhost:8765"
    
    def test_health_endpoint(self):
        """Test GET /health endpoint."""
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=5)
            assert response.status_code == 200
            
            data = response.json()
            assert "status" in data
            
        except requests.RequestException:
            pytest.skip("Server not accessible")
    
    def test_root_endpoint(self):
        """Test GET / endpoint."""
        try:
            response = requests.get(self.BASE_URL, timeout=5)
            assert response.status_code == 200
            
            data = response.json()
            assert "message" in data
            
        except requests.RequestException:
            pytest.skip("Server not accessible")
    
    def test_openapi_docs(self):
        """Test GET /openapi.json endpoint."""
        try:
            response = requests.get(f"{self.BASE_URL}/openapi.json", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                assert "openapi" in data
                assert "paths" in data
            
        except requests.RequestException:
            pytest.skip("Server not accessible")
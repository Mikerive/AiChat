"""
Backend package

FastAPI application with routes, services, and data access objects.
"""

from .main import create_app

__all__ = [
    "create_app",
]

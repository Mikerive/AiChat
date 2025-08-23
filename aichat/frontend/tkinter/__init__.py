"""
Tkinter Frontend Package
Modern, modular Tkinter GUI for VTuber application
"""

from .app import VTuberApp, main
from .components import *
from .utils import *
from .backend_client import BackendClient

__all__ = ['VTuberApp', 'main', 'BackendClient']
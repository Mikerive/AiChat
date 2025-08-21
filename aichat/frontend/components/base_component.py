"""
Base component class for GUI components
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BaseComponent:
    """Base class for all GUI components"""

    def __init__(self, parent: tk.Widget, main_app: Optional[Any] = None):
        self.parent = parent
        self.main_app = main_app
        self.frame: Optional[ttk.Frame] = None
        self.widgets: Dict[str, tk.Widget] = {}

    def create(self):
        """Create the component's UI"""
        raise NotImplementedError("Subclasses must implement create()")

    def destroy(self):
        """Destroy the component's UI"""
        if self.frame:
            self.frame.destroy()
            self.frame = None
            self.widgets.clear()

    def get_widget(self, name: str) -> Optional[tk.Widget]:
        """Get a widget by name"""
        return self.widgets.get(name)

    def add_widget(self, name: str, widget: tk.Widget):
        """Add a widget to the component"""
        self.widgets[name] = widget

    def refresh(self):
        """Refresh the component's data"""

    def update_status(self, status: str):
        """Update status display"""

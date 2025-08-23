"""
Base component class for all GUI components
"""

import tkinter as tk
from tkinter import ttk
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
import logging

from ..utils import safe_call
from ..theme import theme

logger = logging.getLogger(__name__)


class BaseComponent(ABC):
    """Base class for all GUI components"""
    
    def __init__(self, parent: tk.Widget, app_controller=None):
        self.parent = parent
        self.app_controller = app_controller
        self.frame = None
        self.widgets = {}
        self.callbacks = {}
        
        self._create_frame()
        self._setup_component()
        
    def _create_frame(self):
        """Create the main frame for this component"""
        self.frame = ttk.Frame(self.parent, style='Main.TFrame')
        
    @abstractmethod
    def _setup_component(self):
        """Setup the component - must be implemented by subclasses"""
        pass
    
    def pack(self, **kwargs):
        """Pack the component frame"""
        self.frame.pack(**kwargs)
        
    def grid(self, **kwargs):
        """Grid the component frame"""  
        self.frame.grid(**kwargs)
        
    def place(self, **kwargs):
        """Place the component frame"""
        self.frame.place(**kwargs)
        
    def configure(self, **kwargs):
        """Configure the component frame"""
        self.frame.configure(**kwargs)
        
    def destroy(self):
        """Destroy the component"""
        if self.frame:
            self.frame.destroy()
            
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for an event"""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
        
    def emit_event(self, event: str, data: Any = None):
        """Emit an event to registered callbacks"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                safe_call(callback, data)
                
    def update_state(self, state: Dict[str, Any]):
        """Update component state - can be overridden by subclasses"""
        pass
        
    def get_state(self) -> Dict[str, Any]:
        """Get component state - can be overridden by subclasses"""
        return {}
        
    def create_labeled_frame(self, parent: tk.Widget, text: str, **kwargs) -> ttk.LabelFrame:
        """Create a labeled frame with consistent styling"""
        frame = ttk.LabelFrame(parent, text=text, **kwargs)
        return frame
        
    def create_button(self, parent: tk.Widget, text: str, command: Callable = None, 
                     style: str = 'Primary.TButton', **kwargs) -> ttk.Button:
        """Create a button with consistent styling"""
        button = ttk.Button(parent, text=text, command=command, style=style, **kwargs)
        return button
        
    def create_label(self, parent: tk.Widget, text: str, 
                    style: str = 'Body.TLabel', **kwargs) -> ttk.Label:
        """Create a label with consistent styling"""
        label = ttk.Label(parent, text=text, style=style, **kwargs)
        return label
        
    def show_error(self, message: str):
        """Show error message"""
        self.emit_event('error', message)
        
    def show_success(self, message: str):
        """Show success message"""
        self.emit_event('success', message)
        
    def show_info(self, message: str):
        """Show info message"""
        self.emit_event('info', message)


class PanelComponent(BaseComponent):
    """Base class for panel components"""
    
    def __init__(self, parent: tk.Widget, title: str, app_controller=None):
        self.title = title
        super().__init__(parent, app_controller)
        
    def _create_frame(self):
        """Create a labeled frame for panels"""
        self.frame = self.create_labeled_frame(self.parent, self.title, 
                                             padding=theme.spacing.md)


class ControlComponent(BaseComponent):
    """Base class for control components (buttons, inputs, etc.)"""
    
    def __init__(self, parent: tk.Widget, app_controller=None):
        super().__init__(parent, app_controller)
        
    def enable(self):
        """Enable the component"""
        for widget in self.widgets.values():
            if hasattr(widget, 'configure'):
                widget.configure(state='normal')
                
    def disable(self):
        """Disable the component"""  
        for widget in self.widgets.values():
            if hasattr(widget, 'configure'):
                widget.configure(state='disabled')
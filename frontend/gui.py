"""
Tkinter GUI for VTuber debugging command center - Refactored with Components
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional, Dict, Any
import logging
import requests
import websockets
import asyncio
import json
import threading

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config import get_settings

# Import components
from components.websocket_handler import WebSocketHandler
from components.status_tab import StatusTab
from components.chat_tab import ChatTab
from components.voice_tab import VoiceTab
from components.logs_tab import LogsTab
from components.config_tab import ConfigTab

logger = logging.getLogger(__name__)


class VTuberGUI:
    """Main GUI application for VTuber debugging - Refactored"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VTuber Backend - Command Center")
        self.root.geometry("1200x800")
        
        # Settings
        self.settings = get_settings()
        self.api_base_url = f"http://{self.settings.api_host}:{self.settings.api_port}"
        
        # State
        self.connected = False
        self.auto_refresh = True
        self.refresh_interval = 1000  # milliseconds
        self.datetime = datetime
        
        # Create WebSocket handler
        self.ws_handler = WebSocketHandler(self)
        
        # Create GUI
        self.create_widgets()
        self.setup_menu()
        
        # Start WebSocket connection
        self.start_websocket()
        
        # Start auto-refresh
        self.start_auto_refresh()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """Create GUI widgets using components"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create components
        self.components = {}
        
        # Status Tab
        status_frame = ttk.Frame(self.notebook)
        self.notebook.add(status_frame, text="System Status")
        self.components['status'] = StatusTab(status_frame, self)
        self.components['status'].create()
        # Ensure the component's internal frame is attached to the tab container
        if getattr(self.components['status'], "frame", None) is not None:
            self.components['status'].frame.pack(fill=tk.BOTH, expand=True)
        
        # Chat Tab
        chat_frame = ttk.Frame(self.notebook)
        self.notebook.add(chat_frame, text="Chat Interface")
        self.components['chat'] = ChatTab(chat_frame, self)
        self.components['chat'].create()
        if getattr(self.components['chat'], "frame", None) is not None:
            self.components['chat'].frame.pack(fill=tk.BOTH, expand=True)
        
        # Voice Tab
        voice_frame = ttk.Frame(self.notebook)
        self.notebook.add(voice_frame, text="Voice Training")
        self.components['voice'] = VoiceTab(voice_frame, self)
        self.components['voice'].create()
        if getattr(self.components['voice'], "frame", None) is not None:
            self.components['voice'].frame.pack(fill=tk.BOTH, expand=True)
        
        # Logs Tab
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="Event Logs")
        self.components['logs'] = LogsTab(logs_frame, self)
        self.components['logs'].create()
        if getattr(self.components['logs'], "frame", None) is not None:
            self.components['logs'].frame.pack(fill=tk.BOTH, expand=True)
        
        # Config Tab
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="Configuration")
        self.components['config'] = ConfigTab(config_frame, self)
        self.components['config'].create()
        if getattr(self.components['config'], "frame", None) is not None:
            self.components['config'].frame.pack(fill=tk.BOTH, expand=True)
        
        # Expose commonly-used tab objects as attributes for compatibility with components
        # (some handlers expect main_app.chat_tab / .logs_tab etc.)
        self.status_tab = self.components.get('status')
        self.chat_tab = self.components.get('chat')
        self.voice_tab = self.components.get('voice')
        self.logs_tab = self.components.get('logs')
        self.config_tab = self.components.get('config')
    
    def setup_menu(self):
        """Setup menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Clear Logs", command=self.clear_logs)
        edit_menu.add_command(label="Refresh All", command=self.refresh_all)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="System Status", command=lambda: self.notebook.select(0))
        view_menu.add_command(label="Chat Interface", command=lambda: self.notebook.select(1))
        view_menu.add_command(label="Voice Training", command=lambda: self.notebook.select(2))
        view_menu.add_command(label="Event Logs", command=lambda: self.notebook.select(3))
        view_menu.add_command(label="Configuration", command=lambda: self.notebook.select(4))
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def start_websocket(self):
        """Start WebSocket connection"""
        self.ws_handler.start()
    
    def toggle_connection(self):
        """Toggle WebSocket connection"""
        if self.connected:
            self.connected = False
            self.ws_handler.disconnect()
        else:
            self.ws_handler.start()
    
    def start_auto_refresh(self):
        """Start auto-refresh timer"""
        if hasattr(self, 'components') and 'logs' in self.components:
            if self.components['logs'].auto_refresh_var.get():
                self.refresh_all()
        
        self.root.after(self.refresh_interval, self.start_auto_refresh)
    
    def refresh_all(self):
        """Refresh all tabs"""
        if hasattr(self, 'components'):
            if 'status' in self.components:
                self.components['status'].refresh_status()
            if 'chat' in self.components:
                self.components['chat'].refresh()
            if 'voice' in self.components:
                self.components['voice'].refresh()
            if 'logs' in self.components:
                self.components['logs'].refresh()
    
    def refresh_status(self):
        """Refresh system status"""
        if hasattr(self, 'components') and 'status' in self.components:
            self.components['status'].refresh_status()
    
    def refresh_characters(self):
        """Refresh character list"""
        if hasattr(self, 'components') and 'chat' in self.components:
            self.components['chat'].refresh_characters()
    
    def refresh_models(self):
        """Refresh voice models"""
        if hasattr(self, 'components') and 'voice' in self.components:
            self.components['voice'].refresh_models()
    
    def refresh_logs(self):
        """Refresh event logs"""
        if hasattr(self, 'components') and 'logs' in self.components:
            self.components['logs'].refresh_logs()
    
    def clear_logs(self):
        """Clear event logs"""
        if hasattr(self, 'components') and 'logs' in self.components:
            self.components['logs'].clear_logs()
    
    def send_chat_message(self, event=None):
        """Send chat message"""
        if hasattr(self, 'components') and 'chat' in self.components:
            self.components['chat'].send_chat_message(event)
    
    def add_chat_message(self, sender: str, message: str):
        """Add chat message to display"""
        if hasattr(self, 'components') and 'chat' in self.components:
            self.components['chat'].add_chat_message(sender, message)
    
    def generate_tts(self):
        """Generate text-to-speech"""
        if hasattr(self, 'components') and 'chat' in self.components:
            self.components['chat'].generate_tts()
    
    def play_audio(self):
        """Play audio file"""
        if hasattr(self, 'components') and 'chat' in self.components:
            self.components['chat'].play_audio()
    
    def upload_audio(self):
        """Upload audio file"""
        if hasattr(self, 'components') and 'voice' in self.components:
            self.components['voice'].upload_audio()
    
    def start_training(self):
        """Start voice training"""
        if hasattr(self, 'components') and 'voice' in self.components:
            self.components['voice'].start_training()
    
    def add_training_progress(self, progress_data: Dict[str, Any]):
        """Add training progress to display"""
        if hasattr(self, 'components') and 'voice' in self.components:
            self.components['voice'].add_training_progress(progress_data)
    
    def add_log(self, message: str):
        """Add log message"""
        if hasattr(self, 'components') and 'logs' in self.components:
            self.components['logs'].add_log(message)
    
    def save_config(self):
        """Save configuration"""
        if hasattr(self, 'components') and 'config' in self.components:
            self.components['config'].save_config()
    
    def reload_config(self):
        """Reload configuration"""
        if hasattr(self, 'components') and 'config' in self.components:
            self.components['config'].reload_config()
    
    def on_character_selected(self, event):
        """Handle character selection"""
        if hasattr(self, 'components') and 'chat' in self.components:
            self.components['chat'].on_character_selected(event)
    
    def update_connection_status(self):
        """Update connection status display"""
        if hasattr(self, 'components') and 'status' in self.components:
            self.components['status'].update_connection_status()
    
    def update_system_status(self, status_data: Dict[str, Any]):
        """Update system status"""
        if hasattr(self, 'components') and 'status' in self.components:
            self.components['status'].update_system_status_display(status_data)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """VTuber Backend - Command Center

Version: 1.0.0
A control interface for the VTuber streaming backend.

Features:
- Real-time system monitoring
- Chat interface with character interaction
- Voice training and model management
- Event logging and filtering
- Configuration management

Created with Python, Tkinter, and FastAPI."""
        
        messagebox.showinfo("About", about_text)
    
    def on_closing(self):
        """Handle window closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            self.connected = False
            if hasattr(self, 'ws_handler'):
                self.ws_handler.disconnect()
            self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = VTuberGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
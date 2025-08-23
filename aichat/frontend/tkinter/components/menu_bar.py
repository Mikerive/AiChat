"""
Menu Bar Component - Application menu and shortcuts
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, Optional, Callable
import logging
import json
import os

from .base import BaseComponent
from ..theme import theme

logger = logging.getLogger(__name__)


class MenuBar(BaseComponent):
    """Application menu bar"""
    
    def __init__(self, parent: tk.Widget, app_controller=None):
        self.menu_bar = None
        super().__init__(parent, app_controller)
        
    def _setup_component(self):
        """Setup the menu bar"""
        # Create menu bar
        menu_colors = theme.get_menu_colors()
        self.menu_bar = tk.Menu(self.parent, **menu_colors)
        
        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0, **menu_colors)
        file_menu.add_command(label="New Chat", command=self._new_chat, accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Import Chat...", command=self._import_chat, accelerator="Ctrl+I")
        file_menu.add_command(label="Export Chat...", command=self._export_chat, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Settings...", command=self._show_settings, accelerator="Ctrl+,")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._exit_app, accelerator="Ctrl+Q")
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        
        # Voice menu
        voice_menu = tk.Menu(self.menu_bar, tearoff=0, **menu_colors)
        voice_menu.add_command(label="Start Recording", command=self._start_recording, accelerator="Ctrl+R")
        voice_menu.add_command(label="Stop Recording", command=self._stop_recording, accelerator="Ctrl+S")
        voice_menu.add_separator()
        voice_menu.add_command(label="Toggle Listening", command=self._toggle_listening, accelerator="Ctrl+L")
        voice_menu.add_separator()
        voice_menu.add_command(label="Audio Settings...", command=self._audio_settings)
        self.menu_bar.add_cascade(label="Voice", menu=voice_menu)
        
        # Backend menu
        backend_menu = tk.Menu(self.menu_bar, tearoff=0, **menu_colors)
        backend_menu.add_command(label="Start Backend", command=self._start_backend)
        backend_menu.add_command(label="Stop Backend", command=self._stop_backend)
        backend_menu.add_command(label="Restart Backend", command=self._restart_backend)
        backend_menu.add_separator()
        backend_menu.add_command(label="Test Connection", command=self._test_connection)
        backend_menu.add_command(label="Backend Status", command=self._backend_status)
        self.menu_bar.add_cascade(label="Backend", menu=backend_menu)
        
        # View menu
        view_menu = tk.Menu(self.menu_bar, tearoff=0, **menu_colors)
        view_menu.add_command(label="Refresh Status", command=self._refresh_status, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_command(label="Clear Chat", command=self._clear_chat, accelerator="Ctrl+Del")
        view_menu.add_command(label="Full Screen", command=self._toggle_fullscreen, accelerator="F11")
        self.menu_bar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0, **menu_colors)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        help_menu.add_command(label="Documentation", command=self._show_docs)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        
        # Configure parent window to use this menu
        try:
            self.parent.config(menu=self.menu_bar)
        except:
            # If parent doesn't support menu config, try to find root window
            root = self.parent
            while root.master:
                root = root.master
            root.config(menu=self.menu_bar)
            
        # Bind keyboard shortcuts
        self._setup_keyboard_shortcuts()
        
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        try:
            root = self.parent
            while root.master:
                root = root.master
                
            # File shortcuts
            root.bind_all("<Control-n>", lambda e: self._new_chat())
            root.bind_all("<Control-i>", lambda e: self._import_chat())
            root.bind_all("<Control-e>", lambda e: self._export_chat())
            root.bind_all("<Control-comma>", lambda e: self._show_settings())
            root.bind_all("<Control-q>", lambda e: self._exit_app())
            
            # Voice shortcuts
            root.bind_all("<Control-r>", lambda e: self._start_recording())
            root.bind_all("<Control-s>", lambda e: self._stop_recording())
            root.bind_all("<Control-l>", lambda e: self._toggle_listening())
            
            # View shortcuts
            root.bind_all("<F5>", lambda e: self._refresh_status())
            root.bind_all("<Control-Delete>", lambda e: self._clear_chat())
            root.bind_all("<F11>", lambda e: self._toggle_fullscreen())
            
        except Exception as e:
            logger.error(f"Failed to setup keyboard shortcuts: {e}")
            
    # File menu actions
    def _new_chat(self):
        """Start new chat"""
        self.emit_event('new_chat_requested')
        
    def _import_chat(self):
        """Import chat history"""
        filename = filedialog.askopenfilename(
            title="Import Chat History",
            filetypes=[
                ("JSON files", "*.json"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    if filename.endswith('.json'):
                        chat_data = json.load(f)
                        self.emit_event('chat_import_requested', chat_data)
                    else:
                        # Plain text import
                        content = f.read()
                        self.emit_event('text_import_requested', content)
                        
                self.show_success(f"Chat imported from {os.path.basename(filename)}")
                
            except Exception as e:
                self.show_error(f"Import failed: {e}")
                
    def _export_chat(self):
        """Export chat history"""
        self.emit_event('chat_export_requested')
        
    def _show_settings(self):
        """Show settings dialog"""
        self._show_settings_dialog()
        
    def _exit_app(self):
        """Exit application"""
        if messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            self.emit_event('app_exit_requested')
            
    # Voice menu actions
    def _start_recording(self):
        """Start voice recording"""
        self.emit_event('voice_recording_start_requested')
        
    def _stop_recording(self):
        """Stop voice recording"""
        self.emit_event('voice_recording_stop_requested')
        
    def _toggle_listening(self):
        """Toggle voice listening"""
        self.emit_event('voice_listening_toggle_requested')
        
    def _audio_settings(self):
        """Show audio settings"""
        self._show_audio_settings_dialog()
        
    # Backend menu actions
    def _start_backend(self):
        """Start backend"""
        self.emit_event('backend_start_requested')
        
    def _stop_backend(self):
        """Stop backend"""
        self.emit_event('backend_stop_requested')
        
    def _restart_backend(self):
        """Restart backend"""
        self.emit_event('backend_restart_requested')
        
    def _test_connection(self):
        """Test backend connection"""
        self.emit_event('backend_test_requested')
        
    def _backend_status(self):
        """Show backend status"""
        self.emit_event('backend_status_requested')
        
    # View menu actions
    def _refresh_status(self):
        """Refresh all status displays"""
        self.emit_event('status_refresh_requested')
        
    def _clear_chat(self):
        """Clear chat display"""
        if messagebox.askokcancel("Clear Chat", "Clear all chat history?"):
            self.emit_event('chat_clear_requested')
            
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.emit_event('fullscreen_toggle_requested')
        
    # Help menu actions
    def _show_shortcuts(self):
        """Show keyboard shortcuts help"""
        shortcuts_text = """Keyboard Shortcuts:

File:
  Ctrl+N - New Chat
  Ctrl+I - Import Chat
  Ctrl+E - Export Chat
  Ctrl+, - Settings
  Ctrl+Q - Exit

Voice:
  Ctrl+R - Start Recording
  Ctrl+S - Stop Recording
  Ctrl+L - Toggle Listening

View:
  F5 - Refresh Status
  Ctrl+Del - Clear Chat
  F11 - Full Screen

Navigation:
  Tab - Next Control
  Shift+Tab - Previous Control
  Enter - Activate Button
  Space - Toggle Checkbox/Radio
"""
        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)
        
    def _show_docs(self):
        """Show documentation"""
        docs_text = """VTuber Voice Interface Documentation

This application provides voice interaction capabilities with AI characters:

Voice Modes:
- Push to Talk: Hold the microphone button while speaking
- Always Listening: Continuously monitors for voice input

Features:
- Real-time speech recognition
- Text-to-speech responses
- Chat history with export/import
- Backend process management
- Audio level monitoring

Getting Started:
1. Start the backend from the Backend menu or panel
2. Choose your voice mode (Push to Talk or Always Listening)
3. Adjust sensitivity settings as needed
4. Start talking to interact with the AI

Troubleshooting:
- Check audio permissions if voice input doesn't work
- Verify microphone is working in system settings
- Ensure backend is running and connected
- Check volume levels and sensitivity settings
"""
        messagebox.showinfo("Documentation", docs_text)
        
    def _show_about(self):
        """Show about dialog"""
        about_text = """VTuber Voice Interface

A voice-enabled chat interface for interacting with AI characters.

Features:
• Real-time voice recognition
• Text-to-speech synthesis
• Interactive chat interface
• Backend process management
• Audio processing and monitoring

Built with Python, Tkinter, and modern AI services.
"""
        messagebox.showinfo("About", about_text)
        
    def _show_settings_dialog(self):
        """Show settings configuration dialog"""
        settings_window = tk.Toplevel(self.parent)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        settings_window.configure(bg=theme.colors.bg_primary)
        settings_window.transient(self.parent)
        settings_window.grab_set()
        
        # Center the window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (settings_window.winfo_width() // 2)
        y = (settings_window.winfo_screenheight() // 2) - (settings_window.winfo_height() // 2)
        settings_window.geometry(f"+{x}+{y}")
        
        # Settings content
        main_frame = ttk.Frame(settings_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Backend settings
        backend_frame = ttk.LabelFrame(main_frame, text="Backend Settings")
        backend_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(backend_frame, text="Backend URL:").pack(anchor=tk.W, padx=5, pady=2)
        url_entry = ttk.Entry(backend_frame, width=40)
        url_entry.pack(fill=tk.X, padx=5, pady=2)
        url_entry.insert(0, "http://localhost:8765")
        
        auto_start_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(backend_frame, text="Auto-start backend", 
                       variable=auto_start_var).pack(anchor=tk.W, padx=5, pady=2)
        
        # Voice settings
        voice_frame = ttk.LabelFrame(main_frame, text="Voice Settings")
        voice_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(voice_frame, text="Default Voice Mode:").pack(anchor=tk.W, padx=5, pady=2)
        mode_var = tk.StringVar(value="push")
        ttk.Radiobutton(voice_frame, text="Push to Talk", variable=mode_var, 
                       value="push").pack(anchor=tk.W, padx=20, pady=1)
        ttk.Radiobutton(voice_frame, text="Always Listening", variable=mode_var, 
                       value="always").pack(anchor=tk.W, padx=20, pady=1)
        
        # UI settings
        ui_frame = ttk.LabelFrame(main_frame, text="Interface Settings")
        ui_frame.pack(fill=tk.X, pady=(0, 10))
        
        auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ui_frame, text="Auto-scroll chat", 
                       variable=auto_scroll_var).pack(anchor=tk.W, padx=5, pady=2)
        
        show_timestamps_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ui_frame, text="Show timestamps", 
                       variable=show_timestamps_var).pack(anchor=tk.W, padx=5, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def save_settings():
            settings = {
                'backend_url': url_entry.get(),
                'auto_start_backend': auto_start_var.get(),
                'voice_mode': mode_var.get(),
                'auto_scroll': auto_scroll_var.get(),
                'show_timestamps': show_timestamps_var.get()
            }
            self.emit_event('settings_changed', settings)
            settings_window.destroy()
            self.show_success("Settings saved")
            
        ttk.Button(button_frame, text="Save", 
                  command=save_settings).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", 
                  command=settings_window.destroy).pack(side=tk.RIGHT)
                  
    def _show_audio_settings_dialog(self):
        """Show audio settings dialog"""
        audio_window = tk.Toplevel(self.parent)
        audio_window.title("Audio Settings")
        audio_window.geometry("350x250")
        audio_window.configure(bg=theme.colors.bg_primary)
        audio_window.transient(self.parent)
        audio_window.grab_set()
        
        # Center the window
        audio_window.update_idletasks()
        x = (audio_window.winfo_screenwidth() // 2) - (audio_window.winfo_width() // 2)
        y = (audio_window.winfo_screenheight() // 2) - (audio_window.winfo_height() // 2)
        audio_window.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(audio_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Sensitivity setting
        ttk.Label(main_frame, text="Voice Sensitivity:").pack(anchor=tk.W, pady=2)
        sensitivity_var = tk.DoubleVar(value=50.0)
        sensitivity_scale = tk.Scale(main_frame, variable=sensitivity_var,
                                   from_=0, to=100, orient=tk.HORIZONTAL,
                                   bg=theme.colors.bg_secondary, fg=theme.colors.text_primary)
        sensitivity_scale.pack(fill=tk.X, pady=5)
        
        # Volume threshold
        ttk.Label(main_frame, text="Volume Threshold:").pack(anchor=tk.W, pady=(10, 2))
        threshold_var = tk.DoubleVar(value=30.0)
        threshold_scale = tk.Scale(main_frame, variable=threshold_var,
                                 from_=0, to=100, orient=tk.HORIZONTAL,
                                 bg=theme.colors.bg_secondary, fg=theme.colors.text_primary)
        threshold_scale.pack(fill=tk.X, pady=5)
        
        # Test button
        test_frame = ttk.Frame(main_frame)
        test_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(test_frame, text="Test Audio", 
                  command=lambda: self.emit_event('audio_test_requested')).pack()
        
        # Save/Cancel buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def save_audio_settings():
            settings = {
                'sensitivity': sensitivity_var.get(),
                'volume_threshold': threshold_var.get()
            }
            self.emit_event('audio_settings_changed', settings)
            audio_window.destroy()
            self.show_success("Audio settings saved")
            
        ttk.Button(button_frame, text="Save", 
                  command=save_audio_settings).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", 
                  command=audio_window.destroy).pack(side=tk.RIGHT)
        
    def update_state(self, state: Dict[str, Any]):
        """Update menu bar state"""
        # Menu states can be updated based on application state
        pass
        
    def get_state(self) -> Dict[str, Any]:
        """Get current menu bar state"""
        return {}
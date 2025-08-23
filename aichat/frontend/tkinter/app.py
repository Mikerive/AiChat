"""
VTuber Voice Interface - Main Tkinter Application
"""

import tkinter as tk
from tkinter import ttk
import threading
import logging
import sys
import os
from typing import Dict, Any, Optional
import time

from .components import (
    StatusPanel, VoiceControlsPanel, ChatDisplayPanel, 
    BackendControlsPanel, MenuBar, CharacterManagerPanel, AudioDevicesPanel
)
from .utils import ThreadSafeQueue, PeriodicTimer
from .backend_client import BackendClient
from .theme import theme, apply_theme

logger = logging.getLogger(__name__)


class VTuberApp:
    """Main VTuber Voice Interface Application"""
    
    def __init__(self):
        self.root = None
        self.components = {}
        self.backend_client = None
        self.message_queue = ThreadSafeQueue()
        self.update_timer = None
        self.is_running = False
        
        self._setup_logging()
        self._create_window()
        self._setup_styles()
        self._create_backend_client()
        self._create_components()
        self._setup_event_handlers()
        self._start_update_loop()
        
    def _setup_logging(self):
        """Setup application logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
    def _create_window(self):
        """Create main application window"""
        self.root = tk.Tk()
        self.root.title("VTuber Voice Interface")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Apply theme
        apply_theme(self.root)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set window icon if available
        try:
            # Try to find an icon file
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass  # Icon not critical
            
    def _setup_styles(self):
        """Setup TTK styles - now handled by theme system"""
        pass  # Theme is applied in _create_window
        
    def _create_backend_client(self):
        """Initialize backend client"""
        self.backend_client = BackendClient("http://localhost:8765")
        logger.info("Backend client initialized")
        
    def _create_components(self):
        """Create all GUI components matching backend API capabilities"""
        # Create main layout with character sidebar and main content
        main_container = ttk.Frame(self.root, style='Main.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, 
                          padx=theme.spacing.md, pady=theme.spacing.md)
        
        # Create menu bar
        self.components['menu_bar'] = MenuBar(self.root, app_controller=self)
        
        # Create horizontal paned window for sidebar and main content
        main_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Character Manager Sidebar (left side)
        sidebar_frame = ttk.Frame(main_paned, style='Main.TFrame')
        main_paned.add(sidebar_frame, weight=0)  # Fixed width
        
        self.components['character_manager'] = CharacterManagerPanel(sidebar_frame, app_controller=self)
        self.components['character_manager'].pack(fill=tk.BOTH, expand=True,
                                                padx=theme.spacing.sm, pady=theme.spacing.sm)
        
        # Main content area (right side)
        content_frame = ttk.Frame(main_paned, style='Main.TFrame')
        main_paned.add(content_frame, weight=1)  # Expandable
        
        # Create notebook for tabbed interface in main content
        self.notebook = ttk.Notebook(content_frame, style='Modern.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, 
                         padx=theme.spacing.sm, pady=theme.spacing.sm)
        
        # Tab 1: Chat Studio - Character chat with history
        chat_frame = ttk.Frame(self.notebook, style='Main.TFrame')
        self.notebook.add(chat_frame, text="💬 Chat Studio")
        
        self.components['chat_display'] = ChatDisplayPanel(chat_frame, app_controller=self)
        self.components['chat_display'].pack(fill=tk.BOTH, expand=True, 
                                           padx=theme.spacing.md, pady=theme.spacing.md)
        
        # Tab 2: Voice Studio - Recording, TTS, voice pipeline
        voice_frame = ttk.Frame(self.notebook, style='Main.TFrame')
        self.notebook.add(voice_frame, text="🎤 Voice Studio")
        
        self.components['voice_controls'] = VoiceControlsPanel(voice_frame, app_controller=self)
        self.components['voice_controls'].pack(fill=tk.BOTH, expand=True, 
                                             padx=theme.spacing.md, pady=theme.spacing.md)
        
        # Tab 3: Audio Devices - Device management, VAD, audio I/O
        audio_frame = ttk.Frame(self.notebook, style='Main.TFrame')
        self.notebook.add(audio_frame, text="🔊 Audio Devices")
        
        self.components['audio_devices'] = AudioDevicesPanel(audio_frame, app_controller=self)
        self.components['audio_devices'].pack(fill=tk.BOTH, expand=True,
                                            padx=theme.spacing.md, pady=theme.spacing.md)
        
        # Tab 4: Training - Voice model training interface
        # TODO: Implement TrainingPanel in next phase
        
        # Tab 5: System Monitor - Status, webhooks, resources
        system_frame = ttk.Frame(self.notebook, style='Main.TFrame')
        self.notebook.add(system_frame, text="📊 System")
        
        # Create a paned window for system tab
        system_paned = ttk.PanedWindow(system_frame, orient=tk.HORIZONTAL)
        system_paned.pack(fill=tk.BOTH, expand=True, 
                         padx=theme.spacing.sm, pady=theme.spacing.sm)
        
        # Left side - System status
        status_frame = ttk.Frame(system_paned, style='Main.TFrame')
        system_paned.add(status_frame, weight=1)
        
        self.components['status_panel'] = StatusPanel(status_frame, app_controller=self)
        self.components['status_panel'].pack(fill=tk.BOTH, expand=True,
                                           padx=theme.spacing.sm, pady=theme.spacing.sm)
        
        # Right side - Backend controls
        backend_frame = ttk.Frame(system_paned, style='Main.TFrame')
        system_paned.add(backend_frame, weight=1)
        
        self.components['backend_controls'] = BackendControlsPanel(backend_frame, app_controller=self)
        self.components['backend_controls'].pack(fill=tk.BOTH, expand=True,
                                               padx=theme.spacing.sm, pady=theme.spacing.sm)
        
        # Tab 6: Settings - Configuration and preferences
        # TODO: Implement SettingsPanel in next phase
        
        logger.info("GUI components created successfully")
        
    def _setup_event_handlers(self):
        """Setup event handlers for component communication"""
        # Backend events
        self._register_event_handler('backend_start_requested', self._on_backend_start_requested)
        self._register_event_handler('backend_stop_requested', self._on_backend_stop_requested)
        self._register_event_handler('backend_restart_requested', self._on_backend_restart_requested)
        self._register_event_handler('backend_test_requested', self._on_backend_test_requested)
        self._register_event_handler('backend_started', self._on_backend_started)
        self._register_event_handler('backend_stopped', self._on_backend_stopped)
        
        # Voice events
        self._register_event_handler('voice_mode_changed', self._on_voice_mode_changed)
        self._register_event_handler('recording_started', self._on_recording_started)
        self._register_event_handler('recording_stopped', self._on_recording_stopped)
        self._register_event_handler('listening_started', self._on_listening_started)
        self._register_event_handler('listening_stopped', self._on_listening_stopped)
        
        # Chat events
        self._register_event_handler('text_message_sent', self._on_text_message_sent)
        self._register_event_handler('message_added', self._on_message_added)
        self._register_event_handler('chat_clear_requested', self._on_chat_clear_requested)
        self._register_event_handler('chat_export_requested', self._on_chat_export_requested)
        
        # Menu events
        self._register_event_handler('new_chat_requested', self._on_new_chat_requested)
        self._register_event_handler('settings_changed', self._on_settings_changed)
        self._register_event_handler('status_refresh_requested', self._on_status_refresh_requested)
        self._register_event_handler('app_exit_requested', self._on_app_exit_requested)
        self._register_event_handler('fullscreen_toggle_requested', self._on_fullscreen_toggle_requested)
        
        # Status events
        self._register_event_handler('error', self._on_error_message)
        self._register_event_handler('success', self._on_success_message)
        self._register_event_handler('info', self._on_info_message)
        
    def _register_event_handler(self, event: str, handler):
        """Register event handler across all components"""
        for component in self.components.values():
            if hasattr(component, 'register_callback'):
                component.register_callback(event, handler)
                
    def _start_update_loop(self):
        """Start the main application update loop"""
        self.is_running = True
        self.update_timer = PeriodicTimer(0.1, self._update)
        self.update_timer.start()
        
    def _update(self):
        """Main application update loop"""
        if not self.is_running:
            return
            
        try:
            # Process message queue
            while not self.message_queue.empty():
                try:
                    message = self.message_queue.get_nowait()
                    self._process_message(message)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
            # Update components that need periodic updates
            if 'status_panel' in self.components:
                # Update uptime display
                pass
                
        except Exception as e:
            logger.error(f"Update loop error: {e}")
            
    def _process_message(self, message: Dict[str, Any]):
        """Process queued messages"""
        msg_type = message.get('type')
        data = message.get('data')
        
        if msg_type == 'ai_response':
            self._handle_ai_response(data)
        elif msg_type == 'voice_transcription':
            self._handle_voice_transcription(data)
        elif msg_type == 'status_update':
            self._handle_status_update(data)
            
    # Event handlers
    def _on_backend_start_requested(self, data=None):
        """Handle backend start request"""
        if 'backend_controls' in self.components:
            self.components['backend_controls'].start_backend()
            
    def _on_backend_stop_requested(self, data=None):
        """Handle backend stop request"""
        if 'backend_controls' in self.components:
            self.components['backend_controls'].stop_backend()
            
    def _on_backend_restart_requested(self, data=None):
        """Handle backend restart request"""
        if 'backend_controls' in self.components:
            self.components['backend_controls'].restart_backend()
            
    def _on_backend_test_requested(self, data=None):
        """Handle backend test request"""
        if 'status_panel' in self.components:
            self.components['status_panel'].test_connection()
            
    def _on_backend_started(self, pid):
        """Handle backend started event"""
        logger.info(f"Backend started with PID: {pid}")
        # Refresh status displays
        if 'status_panel' in self.components:
            self.components['status_panel'].refresh_status()
            
    def _on_backend_stopped(self, data=None):
        """Handle backend stopped event"""
        logger.info("Backend stopped")
        # Refresh status displays
        if 'status_panel' in self.components:
            self.components['status_panel'].refresh_status()
            
    def _on_voice_mode_changed(self, mode):
        """Handle voice mode change"""
        logger.info(f"Voice mode changed to: {mode}")
        
    def _on_recording_started(self, data=None):
        """Handle recording started"""
        logger.info("Voice recording started")
        # TODO: Start actual voice recording
        
    def _on_recording_stopped(self, data=None):
        """Handle recording stopped"""
        logger.info("Voice recording stopped")
        # TODO: Process recorded audio
        
    def _on_listening_started(self, data=None):
        """Handle listening started"""
        logger.info("Always listening activated")
        # TODO: Start continuous voice monitoring
        
    def _on_listening_stopped(self, data=None):
        """Handle listening stopped"""
        logger.info("Always listening deactivated")
        # TODO: Stop continuous voice monitoring
        
    def _on_text_message_sent(self, text):
        """Handle text message sent"""
        logger.info(f"Text message sent: {text[:50]}...")
        # TODO: Send to backend for processing
        threading.Thread(target=self._process_text_message, args=(text,), daemon=True).start()
        
    def _on_message_added(self, message):
        """Handle message added to chat"""
        pass  # Chat display handles this
        
    def _on_chat_clear_requested(self, data=None):
        """Handle chat clear request"""
        if 'chat_display' in self.components:
            self.components['chat_display'].clear_chat()
            
    def _on_chat_export_requested(self, data=None):
        """Handle chat export request"""
        if 'chat_display' in self.components:
            self.components['chat_display'].export_chat()
            
    def _on_new_chat_requested(self, data=None):
        """Handle new chat request"""
        self._on_chat_clear_requested()
        if 'chat_display' in self.components:
            self.components['chat_display'].add_system_message("New conversation started", "info")
            
    def _on_settings_changed(self, settings):
        """Handle settings changed"""
        logger.info(f"Settings changed: {settings}")
        
        # Update components with new settings
        for component in self.components.values():
            if hasattr(component, 'update_state'):
                component.update_state(settings)
                
    def _on_status_refresh_requested(self, data=None):
        """Handle status refresh request"""
        if 'status_panel' in self.components:
            self.components['status_panel'].refresh_status()
            
    def _on_app_exit_requested(self, data=None):
        """Handle app exit request"""
        self._on_closing()
        
    def _on_fullscreen_toggle_requested(self, data=None):
        """Handle fullscreen toggle request"""
        if self.root.attributes('-fullscreen'):
            self.root.attributes('-fullscreen', False)
        else:
            self.root.attributes('-fullscreen', True)
            
    def _on_error_message(self, message):
        """Handle error message"""
        logger.error(message)
        # Could show toast notification or status bar message
        
    def _on_success_message(self, message):
        """Handle success message"""
        logger.info(message)
        # Could show toast notification or status bar message
        
    def _on_info_message(self, message):
        """Handle info message"""
        logger.info(message)
        # Could show toast notification or status bar message
        
    def _process_text_message(self, text: str):
        """Process text message in background thread"""
        try:
            if not self.backend_client:
                logger.error("Backend client not initialized")
                return
                
            # Send message to backend API
            logger.info(f"Sending message to backend: {text[:50]}...")
            result = self.backend_client.send_chat_message(text, "assistant")
            
            def add_response():
                if 'chat_display' in self.components:
                    if result.get('status') == 'error':
                        # Show error message
                        error_msg = result.get('message', 'Unknown error occurred')
                        self.components['chat_display'].add_system_message(
                            f"Error: {error_msg}", "error")
                    else:
                        # Add AI response
                        response_text = result.get('response', 'No response received')
                        metadata = {
                            'model_used': result.get('model_used'),
                            'emotion': result.get('emotion')
                        }
                        self.components['chat_display'].add_ai_response(response_text, metadata)
                    
            self.root.after(0, add_response)
            
        except Exception as e:
            logger.error(f"Error processing text message: {e}")
            def add_error():
                if 'chat_display' in self.components:
                    self.components['chat_display'].add_system_message(
                        f"Connection error: {str(e)}", "error")
            self.root.after(0, add_error)
            
    def _handle_ai_response(self, response):
        """Handle AI response from backend"""
        if 'chat_display' in self.components:
            self.components['chat_display'].add_ai_response(response)
            
    def _handle_voice_transcription(self, transcription):
        """Handle voice transcription"""
        if 'chat_display' in self.components:
            confidence = transcription.get('confidence', 1.0)
            text = transcription.get('text', '')
            self.components['chat_display'].add_voice_message(text, confidence)
            
    def _handle_status_update(self, status):
        """Handle status update"""
        # Update relevant components with status information
        pass
        
    def _on_closing(self):
        """Handle window closing"""
        logger.info("Application closing...")
        
        self.is_running = False
        
        # Stop update timer
        if self.update_timer:
            self.update_timer.stop()
            
        # Cleanup components
        for component in self.components.values():
            if hasattr(component, 'cleanup'):
                try:
                    component.cleanup()
                except Exception as e:
                    logger.error(f"Error during component cleanup: {e}")
                    
        # Destroy window
        self.root.quit()
        self.root.destroy()
        
    def run(self):
        """Run the application"""
        logger.info("Starting VTuber Voice Interface...")
        
        try:
            # Show welcome message
            if 'chat_display' in self.components:
                self.components['chat_display'].add_system_message(
                    "Welcome to VTuber Voice Interface! 🎤✨", "system")
                    
            # Start main loop
            self.root.mainloop()
            
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.error(f"Application error: {e}")
        finally:
            logger.info("Application shutdown complete")


def main():
    """Main entry point"""
    try:
        app = VTuberApp()
        app.run()
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
"""
Voice Controls Panel - Voice interaction and audio controls
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
import threading
import time
import logging

from .base import PanelComponent
from ..theme import theme

logger = logging.getLogger(__name__)


class VoiceControlsPanel(PanelComponent):
    """Panel for voice interaction controls"""
    
    def __init__(self, parent: tk.Widget, app_controller=None):
        self.voice_mode = "push"  # "push" or "always"
        self.is_recording = False
        self.is_listening = False
        self.volume_level = 0.0
        self.audio_available = self._check_audio_availability()
        super().__init__(parent, "Voice Controls", app_controller)
        
    def _setup_component(self):
        """Setup voice controls"""
        # Voice mode selection
        mode_frame = ttk.Frame(self.frame)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.create_label(mode_frame, "Voice Mode:", style='Heading.TLabel').pack(anchor=tk.W)
        
        mode_select_frame = ttk.Frame(mode_frame)
        mode_select_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.widgets['voice_mode_var'] = tk.StringVar(value=self.voice_mode)
        
        self.widgets['push_radio'] = ttk.Radiobutton(
            mode_select_frame, text="Push to Talk",
            variable=self.widgets['voice_mode_var'], value="push",
            command=self._on_mode_change)
        self.widgets['push_radio'].pack(side=tk.LEFT, padx=(0, 10))
        
        self.widgets['always_radio'] = ttk.Radiobutton(
            mode_select_frame, text="Always Listening", 
            variable=self.widgets['voice_mode_var'], value="always",
            command=self._on_mode_change)
        self.widgets['always_radio'].pack(side=tk.LEFT)
        
        # Voice control buttons
        controls_frame = ttk.Frame(self.frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Push to talk button
        self.widgets['talk_button'] = tk.Button(
            controls_frame, text="🎤 Hold to Talk", 
            font=theme.fonts.subheading, bg=theme.colors.success, fg=theme.colors.text_white,
            activebackground=theme.colors.danger, activeforeground=theme.colors.text_white,
            relief='solid', bd=2, padx=15, pady=8)
        self.widgets['talk_button'].pack(side=tk.LEFT, padx=(0, 10))
        
        # Bind mouse events for push-to-talk
        self.widgets['talk_button'].bind("<ButtonPress-1>", self._start_recording)
        self.widgets['talk_button'].bind("<ButtonRelease-1>", self._stop_recording)
        
        # Always listening button
        self.widgets['listen_button'] = tk.Button(
            controls_frame, text="🔊 Start Listening",
            font=theme.fonts.subheading, bg=theme.colors.accent_primary, fg=theme.colors.text_white,
            activebackground=theme.colors.danger, activeforeground=theme.colors.text_white,
            relief='solid', bd=2, padx=15, pady=8,
            command=self._toggle_listening)
        self.widgets['listen_button'].pack(side=tk.LEFT)
        
        # Volume display
        volume_frame = ttk.Frame(self.frame)
        volume_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.create_label(volume_frame, "Volume Level:", style='Heading.TLabel').pack(anchor=tk.W)
        
        volume_display_frame = ttk.Frame(volume_frame)
        volume_display_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.widgets['volume_var'] = tk.DoubleVar()
        self.widgets['volume_bar'] = ttk.Progressbar(
            volume_display_frame, variable=self.widgets['volume_var'],
            maximum=100, length=200, mode='determinate')
        self.widgets['volume_bar'].pack(side=tk.LEFT, padx=(0, 10))
        
        self.widgets['volume_label'] = self.create_label(
            volume_display_frame, "0%", style='Normal.TLabel')
        self.widgets['volume_label'].pack(side=tk.LEFT)
        
        # Audio settings
        settings_frame = ttk.Frame(self.frame)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.create_label(settings_frame, "Audio Settings:", style='Heading.TLabel').pack(anchor=tk.W)
        
        settings_controls_frame = ttk.Frame(settings_frame)
        settings_controls_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Sensitivity slider
        self.create_label(settings_controls_frame, "Sensitivity:", style='Normal.TLabel').pack(anchor=tk.W)
        self.widgets['sensitivity_var'] = tk.DoubleVar(value=50.0)
        self.widgets['sensitivity_scale'] = tk.Scale(
            settings_controls_frame, variable=self.widgets['sensitivity_var'],
            from_=0, to=100, orient=tk.HORIZONTAL, length=200,
            bg=theme.colors.bg_primary, fg=theme.colors.text_primary,
            highlightthickness=1, highlightcolor=theme.colors.accent_primary,
            troughcolor=theme.colors.bg_tertiary, relief='solid', bd=1)
        self.widgets['sensitivity_scale'].pack(fill=tk.X, pady=(2, 5))
        
        # Audio status
        status_frame = ttk.Frame(self.frame)
        status_frame.pack(fill=tk.X)
        
        self.widgets['audio_status'] = self.create_label(
            status_frame, self._get_audio_status_text(), style='Normal.TLabel')
        self.widgets['audio_status'].pack(anchor=tk.W)
        
        # Initialize UI state
        self._update_ui_state()
        
        # Start volume monitoring if audio is available
        if self.audio_available:
            self._start_volume_monitoring()
            
    def _check_audio_availability(self) -> bool:
        """Check if audio is available"""
        try:
            import pyaudio
            audio = pyaudio.PyAudio()
            
            # Try to get default input device
            try:
                device_info = audio.get_default_input_device_info()
                audio.terminate()
                return True
            except:
                audio.terminate()
                return False
                
        except ImportError:
            return False
        except Exception as e:
            logger.error(f"Audio check failed: {e}")
            return False
            
    def _get_audio_status_text(self) -> str:
        """Get audio status text"""
        if self.audio_available:
            if self.is_recording:
                return "🔴 Recording..."
            elif self.is_listening:
                return "👂 Listening..."
            else:
                return "🎤 Audio Ready"
        else:
            return "❌ Audio Not Available"
            
    def _on_mode_change(self):
        """Handle voice mode change"""
        self.voice_mode = self.widgets['voice_mode_var'].get()
        self._update_ui_state()
        
        # Stop any active listening/recording
        if self.is_listening:
            self._toggle_listening()
        if self.is_recording:
            self.is_recording = False
            
        self.emit_event('voice_mode_changed', self.voice_mode)
        self.show_info(f"Voice mode: {self.voice_mode.title()}")
        
    def _update_ui_state(self):
        """Update UI based on current state"""
        if not self.audio_available:
            # Disable all controls if no audio
            self.widgets['talk_button'].configure(state='disabled')
            self.widgets['listen_button'].configure(state='disabled')
            self.widgets['push_radio'].configure(state='disabled')
            self.widgets['always_radio'].configure(state='disabled')
            return
            
        # Enable/disable controls based on mode
        if self.voice_mode == "push":
            self.widgets['talk_button'].configure(state='normal')
            self.widgets['listen_button'].configure(state='disabled')
        else:  # always listening
            self.widgets['talk_button'].configure(state='disabled')
            self.widgets['listen_button'].configure(state='normal')
            
        # Update button texts
        if self.is_listening:
            self.widgets['listen_button'].configure(
                text="🔇 Stop Listening", bg=theme.colors.danger)
        else:
            self.widgets['listen_button'].configure(
                text="🔊 Start Listening", bg=theme.colors.accent_primary)
            
        if self.is_recording:
            self.widgets['talk_button'].configure(
                text="🔴 Recording...", bg=theme.colors.danger)
        else:
            self.widgets['talk_button'].configure(
                text="🎤 Hold to Talk", bg=theme.colors.success)
            
        # Update status
        self.widgets['audio_status'].configure(text=self._get_audio_status_text())
        
    def _start_recording(self, event=None):
        """Start recording in push-to-talk mode"""
        if not self.audio_available or self.voice_mode != "push":
            return
            
        self.is_recording = True
        self._update_ui_state()
        self.emit_event('recording_started')
        self.show_info("🎤 Recording started")
        
    def _stop_recording(self, event=None):
        """Stop recording in push-to-talk mode"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        self._update_ui_state()
        self.emit_event('recording_stopped')
        self.show_info("⏹️ Recording stopped")
        
    def _toggle_listening(self):
        """Toggle always listening mode"""
        if not self.audio_available or self.voice_mode != "always":
            return
            
        self.is_listening = not self.is_listening
        self._update_ui_state()
        
        if self.is_listening:
            self.emit_event('listening_started')
            self.show_success("👂 Always listening activated")
        else:
            self.emit_event('listening_stopped')
            self.show_info("⏸️ Always listening deactivated")
            
    def _start_volume_monitoring(self):
        """Start volume level monitoring"""
        def monitor_volume():
            while True:
                if self.is_recording or self.is_listening:
                    # Simulate volume level (replace with actual audio capture)
                    import random
                    volume = random.randint(0, 100)
                    self._update_volume_display(volume)
                else:
                    self._update_volume_display(0)
                time.sleep(0.1)
                
        if self.audio_available:
            threading.Thread(target=monitor_volume, daemon=True).start()
            
    def _update_volume_display(self, level: float):
        """Update volume display"""
        self.volume_level = level
        
        def update_ui():
            self.widgets['volume_var'].set(level)
            self.widgets['volume_label'].configure(text=f"{level:.0f}%")
            
        # Schedule UI update on main thread
        self.frame.after(0, update_ui)
        
    def update_state(self, state: Dict[str, Any]):
        """Update voice controls state"""
        if 'voice_mode' in state:
            self.voice_mode = state['voice_mode']
            self.widgets['voice_mode_var'].set(self.voice_mode)
            self._update_ui_state()
            
        if 'sensitivity' in state:
            self.widgets['sensitivity_var'].set(state['sensitivity'])
            
    def get_state(self) -> Dict[str, Any]:
        """Get current voice controls state"""
        return {
            'voice_mode': self.voice_mode,
            'is_recording': self.is_recording,
            'is_listening': self.is_listening,
            'volume_level': self.volume_level,
            'sensitivity': self.widgets['sensitivity_var'].get(),
            'audio_available': self.audio_available
        }
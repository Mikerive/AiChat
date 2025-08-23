"""
Audio Devices Panel - Device management, selection, and real-time monitoring
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List, Optional, Tuple
import threading
import time
import logging
import json

from .base import PanelComponent
from ..theme import theme
from ..utils import format_bytes, format_frequency

logger = logging.getLogger(__name__)


class AudioDevicesPanel(PanelComponent):
    """Panel for audio device management and monitoring"""
    
    def __init__(self, parent: tk.Widget, app_controller=None):
        self.input_devices: List[Dict[str, Any]] = []
        self.output_devices: List[Dict[str, Any]] = []
        self.current_input_device: Optional[Dict[str, Any]] = None
        self.current_output_device: Optional[Dict[str, Any]] = None
        self.audio_status: Dict[str, Any] = {}
        self.monitoring_active = False
        self.monitor_thread = None
        super().__init__(parent, "Audio Devices", app_controller)
        
    def _setup_component(self):
        """Setup audio devices interface"""
        # Create main paned window for input/output sections
        main_paned = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Input devices section
        input_frame = ttk.LabelFrame(main_paned, text="Input Devices (Microphones)", 
                                   style='Modern.TLabelframe')
        main_paned.add(input_frame, weight=1)
        
        self._setup_input_section(input_frame)
        
        # Output devices section  
        output_frame = ttk.LabelFrame(main_paned, text="Output Devices (Speakers)", 
                                    style='Modern.TLabelframe')
        main_paned.add(output_frame, weight=1)
        
        self._setup_output_section(output_frame)
        
        # Audio monitoring section
        monitor_frame = ttk.LabelFrame(self.frame, text="Real-time Audio Monitor", 
                                     style='Modern.TLabelframe')
        monitor_frame.pack(fill=tk.X, pady=(0, 10))
        
        self._setup_monitor_section(monitor_frame)
        
        # Control buttons
        control_frame = ttk.Frame(self.frame)
        control_frame.pack(fill=tk.X)
        
        self.widgets['refresh_btn'] = self.create_button(
            control_frame, "🔄 Refresh Devices", command=self.refresh_devices)
        self.widgets['refresh_btn'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['test_audio_btn'] = self.create_button(
            control_frame, "🔊 Test Audio System", command=self._test_audio_system)
        self.widgets['test_audio_btn'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['advanced_btn'] = self.create_button(
            control_frame, "⚙️ Advanced Settings", command=self._open_advanced_settings)
        self.widgets['advanced_btn'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['diagnostics_btn'] = self.create_button(
            control_frame, "🔍 Audio Diagnostics", command=self._run_audio_diagnostics)
        self.widgets['diagnostics_btn'].pack(side=tk.RIGHT)
        
        # Load initial device list
        self.refresh_devices()
        
    def _setup_input_section(self, parent):
        """Setup input devices section"""
        # Device list
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Input device listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.widgets['input_listbox'] = tk.Listbox(
            list_container,
            font=theme.fonts.body,
            bg=theme.colors.bg_primary,
            fg=theme.colors.text_primary,
            selectbackground=theme.colors.accent_primary,
            selectforeground=theme.colors.text_white,
            relief='solid', bd=1,
            highlightcolor=theme.colors.accent_primary,
            highlightthickness=1,
            height=6
        )
        
        input_scroll = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.widgets['input_listbox'].configure(yscrollcommand=input_scroll.set)
        input_scroll.configure(command=self.widgets['input_listbox'].yview)
        
        self.widgets['input_listbox'].pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.widgets['input_listbox'].bind('<<ListboxSelect>>', self._on_input_device_select)
        
        # Input device info
        input_info_frame = ttk.Frame(list_frame)
        input_info_frame.pack(fill=tk.X)
        
        # Sample rate
        self.create_label(input_info_frame, "Sample Rate:", style='Heading.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.widgets['input_sample_rate'] = self.create_label(
            input_info_frame, "44.1kHz", style='Normal.TLabel')
        self.widgets['input_sample_rate'].grid(row=0, column=1, sticky=tk.W)
        
        # Channels
        self.create_label(input_info_frame, "Channels:", style='Heading.TLabel').grid(
            row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(2, 0))
        self.widgets['input_channels'] = self.create_label(
            input_info_frame, "Mono", style='Normal.TLabel')
        self.widgets['input_channels'].grid(row=1, column=1, sticky=tk.W, pady=(2, 0))
        
        # Test button
        self.widgets['test_input_btn'] = self.create_button(
            input_info_frame, "🎤 Test Microphone", 
            command=self._test_input_device, style='Success.TButton')
        self.widgets['test_input_btn'].grid(row=2, column=0, columnspan=2, 
                                          sticky=tk.W, pady=(10, 0))
        
    def _setup_output_section(self, parent):
        """Setup output devices section"""
        # Device list
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Output device listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.widgets['output_listbox'] = tk.Listbox(
            list_container,
            font=theme.fonts.body,
            bg=theme.colors.bg_primary,
            fg=theme.colors.text_primary,
            selectbackground=theme.colors.accent_primary,
            selectforeground=theme.colors.text_white,
            relief='solid', bd=1,
            highlightcolor=theme.colors.accent_primary,
            highlightthickness=1,
            height=6
        )
        
        output_scroll = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.widgets['output_listbox'].configure(yscrollcommand=output_scroll.set)
        output_scroll.configure(command=self.widgets['output_listbox'].yview)
        
        self.widgets['output_listbox'].pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        output_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.widgets['output_listbox'].bind('<<ListboxSelect>>', self._on_output_device_select)
        
        # Output device info and controls
        output_info_frame = ttk.Frame(list_frame)
        output_info_frame.pack(fill=tk.X)
        
        # Volume control
        self.create_label(output_info_frame, "Volume:", style='Heading.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        volume_frame = ttk.Frame(output_info_frame)
        volume_frame.grid(row=0, column=1, sticky=tk.W)
        
        self.widgets['volume_var'] = tk.DoubleVar(value=75.0)
        self.widgets['volume_scale'] = tk.Scale(
            volume_frame, variable=self.widgets['volume_var'],
            from_=0, to=100, orient=tk.HORIZONTAL, length=150,
            bg=theme.colors.bg_primary, fg=theme.colors.text_primary,
            highlightthickness=0, troughcolor=theme.colors.bg_tertiary,
            relief='solid', bd=1, command=self._on_volume_change
        )
        self.widgets['volume_scale'].pack(side=tk.LEFT)
        
        self.widgets['volume_label'] = self.create_label(
            volume_frame, "75%", style='Normal.TLabel')
        self.widgets['volume_label'].pack(side=tk.LEFT, padx=(5, 0))
        
        # Mute toggle
        self.widgets['mute_var'] = tk.BooleanVar()
        self.widgets['mute_check'] = ttk.Checkbutton(
            output_info_frame, text="🔇 Mute", 
            variable=self.widgets['mute_var'], command=self._on_mute_toggle)
        self.widgets['mute_check'].grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Test button
        self.widgets['test_output_btn'] = self.create_button(
            output_info_frame, "🔊 Test Speakers", 
            command=self._test_output_device, style='Success.TButton')
        self.widgets['test_output_btn'].grid(row=2, column=0, columnspan=2, 
                                           sticky=tk.W, pady=(10, 0))
        
    def _setup_monitor_section(self, parent):
        """Setup audio monitoring section"""
        monitor_content = ttk.Frame(parent)
        monitor_content.pack(fill=tk.X, padx=10, pady=10)
        
        # Input level meter
        self.create_label(monitor_content, "Input Level:", style='Heading.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        input_meter_frame = ttk.Frame(monitor_content)
        input_meter_frame.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        self.widgets['input_level_var'] = tk.DoubleVar()
        self.widgets['input_level_bar'] = ttk.Progressbar(
            input_meter_frame, variable=self.widgets['input_level_var'],
            maximum=100, length=200, mode='determinate')
        self.widgets['input_level_bar'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['input_status'] = self.create_label(
            input_meter_frame, "🎤 Ready", style='Normal.TLabel')
        self.widgets['input_status'].pack(side=tk.LEFT)
        
        # Output level meter
        self.create_label(monitor_content, "Output Level:", style='Heading.TLabel').grid(
            row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        
        output_meter_frame = ttk.Frame(monitor_content)
        output_meter_frame.grid(row=1, column=1, sticky=tk.W, padx=(0, 20), pady=(5, 0))
        
        self.widgets['output_level_var'] = tk.DoubleVar()
        self.widgets['output_level_bar'] = ttk.Progressbar(
            output_meter_frame, variable=self.widgets['output_level_var'],
            maximum=100, length=200, mode='determinate')
        self.widgets['output_level_bar'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['output_status'] = self.create_label(
            output_meter_frame, "🔊 Ready", style='Normal.TLabel')
        self.widgets['output_status'].pack(side=tk.LEFT)
        
        # Monitoring controls
        self.widgets['monitor_toggle'] = self.create_button(
            monitor_content, "▶️ Start Monitoring", 
            command=self._toggle_monitoring, style='Accent.TButton')
        self.widgets['monitor_toggle'].grid(row=2, column=0, columnspan=2, 
                                          sticky=tk.W, pady=(10, 0))
        
    def _on_input_device_select(self, event=None):
        """Handle input device selection"""
        selection = self.widgets['input_listbox'].curselection()
        if not selection:
            return
            
        try:
            index = selection[0]
            if 0 <= index < len(self.input_devices):
                device = self.input_devices[index]
                self._set_input_device(device)
        except Exception as e:
            logger.error(f"Error selecting input device: {e}")
            
    def _on_output_device_select(self, event=None):
        """Handle output device selection"""
        selection = self.widgets['output_listbox'].curselection()
        if not selection:
            return
            
        try:
            index = selection[0]
            if 0 <= index < len(self.output_devices):
                device = self.output_devices[index]
                self._set_output_device(device)
        except Exception as e:
            logger.error(f"Error selecting output device: {e}")
            
    def _set_input_device(self, device: Dict[str, Any]):
        """Set input device and update UI"""
        try:
            if hasattr(self.app_controller, 'backend_client'):
                def set_device():
                    try:
                        result = self.app_controller.backend_client.set_input_device(device['index'])
                        
                        def on_success():
                            self.current_input_device = device
                            self._update_input_device_info(device)
                            self.show_success(f"Input device set: {device['name']}")
                            
                        def on_error(error_msg):
                            self.show_error(f"Failed to set input device: {error_msg}")
                            
                        if result.get('status') == 'success':
                            self.frame.after(0, on_success)
                        else:
                            self.frame.after(0, lambda: on_error(result.get('message', 'Unknown error')))
                            
                    except Exception as e:
                        self.frame.after(0, lambda: on_error(str(e)))
                        
                threading.Thread(target=set_device, daemon=True).start()
            else:
                # Fallback for offline mode
                self.current_input_device = device
                self._update_input_device_info(device)
                
        except Exception as e:
            logger.error(f"Error setting input device: {e}")
            
    def _set_output_device(self, device: Dict[str, Any]):
        """Set output device and update UI"""
        try:
            if hasattr(self.app_controller, 'backend_client'):
                def set_device():
                    try:
                        result = self.app_controller.backend_client.set_output_device(device['index'])
                        
                        def on_success():
                            self.current_output_device = device
                            self._update_output_device_info(device)
                            self.show_success(f"Output device set: {device['name']}")
                            
                        def on_error(error_msg):
                            self.show_error(f"Failed to set output device: {error_msg}")
                            
                        if result.get('status') == 'success':
                            self.frame.after(0, on_success)
                        else:
                            self.frame.after(0, lambda: on_error(result.get('message', 'Unknown error')))
                            
                    except Exception as e:
                        self.frame.after(0, lambda: on_error(str(e)))
                        
                threading.Thread(target=set_device, daemon=True).start()
            else:
                # Fallback for offline mode
                self.current_output_device = device
                self._update_output_device_info(device)
                
        except Exception as e:
            logger.error(f"Error setting output device: {e}")
            
    def _update_input_device_info(self, device: Dict[str, Any]):
        """Update input device information display"""
        sample_rate = device.get('default_sample_rate', 44100)
        channels = device.get('max_input_channels', 1)
        
        self.widgets['input_sample_rate'].configure(text=format_frequency(sample_rate))
        self.widgets['input_channels'].configure(text=f"{channels} channel{'s' if channels > 1 else ''}")
        
    def _update_output_device_info(self, device: Dict[str, Any]):
        """Update output device information display"""
        # Update any output-specific information if needed
        pass
        
    def _on_volume_change(self, value):
        """Handle volume slider change"""
        volume = float(value) / 100.0
        self.widgets['volume_label'].configure(text=f"{int(float(value))}%")
        
        # Apply volume change to backend
        if hasattr(self.app_controller, 'backend_client'):
            def set_volume():
                try:
                    result = self.app_controller.backend_client.set_volume(volume)
                    # Volume change feedback handled by backend
                except Exception as e:
                    logger.error(f"Error setting volume: {e}")
                    
            threading.Thread(target=set_volume, daemon=True).start()
            
    def _on_mute_toggle(self):
        """Handle mute toggle"""
        is_muted = self.widgets['mute_var'].get()
        if is_muted:
            self.widgets['volume_scale'].configure(state='disabled')
            # Store current volume and set to 0
            self._stored_volume = self.widgets['volume_var'].get()
            self._on_volume_change(0)
        else:
            self.widgets['volume_scale'].configure(state='normal')
            # Restore previous volume
            if hasattr(self, '_stored_volume'):
                self.widgets['volume_var'].set(self._stored_volume)
                self._on_volume_change(self._stored_volume)
                
    def _test_input_device(self):
        """Test input device"""
        if not self.current_input_device:
            self.show_warning("Please select an input device first")
            return
            
        self.widgets['test_input_btn'].configure(text="Testing...", state='disabled')
        
        def test_input():
            try:
                if hasattr(self.app_controller, 'backend_client'):
                    # Test recording for 2 seconds
                    result = self.app_controller.backend_client.record_audio(duration=2.0)
                    
                    def on_complete():
                        self.widgets['test_input_btn'].configure(
                            text="🎤 Test Microphone", state='normal')
                        if result.get('status') == 'success':
                            self.show_success("Microphone test completed successfully")
                        else:
                            self.show_error(f"Microphone test failed: {result.get('message', 'Unknown error')}")
                            
                    self.frame.after(0, on_complete)
                else:
                    # Simulate test
                    time.sleep(2)
                    def on_complete():
                        self.widgets['test_input_btn'].configure(
                            text="🎤 Test Microphone", state='normal')
                        self.show_success("Microphone test completed (simulated)")
                    self.frame.after(0, on_complete)
                    
            except Exception as e:
                def on_error():
                    self.widgets['test_input_btn'].configure(
                        text="🎤 Test Microphone", state='normal')
                    self.show_error(f"Test failed: {e}")
                self.frame.after(0, on_error)
                
        threading.Thread(target=test_input, daemon=True).start()
        
    def _test_output_device(self):
        """Test output device"""
        if not self.current_output_device:
            self.show_warning("Please select an output device first")
            return
            
        self.widgets['test_output_btn'].configure(text="Testing...", state='disabled')
        
        def test_output():
            try:
                if hasattr(self.app_controller, 'backend_client'):
                    # Generate and play test tone
                    result = self.app_controller.backend_client.generate_tts(
                        text="This is a test of the audio output device.",
                        character_id="assistant"
                    )
                    
                    def on_complete():
                        self.widgets['test_output_btn'].configure(
                            text="🔊 Test Speakers", state='normal')
                        if result.get('status') == 'success':
                            self.show_success("Speaker test completed successfully")
                        else:
                            self.show_error(f"Speaker test failed: {result.get('message', 'Unknown error')}")
                            
                    self.frame.after(0, on_complete)
                else:
                    # Simulate test
                    time.sleep(2)
                    def on_complete():
                        self.widgets['test_output_btn'].configure(
                            text="🔊 Test Speakers", state='normal')
                        self.show_success("Speaker test completed (simulated)")
                    self.frame.after(0, on_complete)
                    
            except Exception as e:
                def on_error():
                    self.widgets['test_output_btn'].configure(
                        text="🔊 Test Speakers", state='normal')
                    self.show_error(f"Test failed: {e}")
                self.frame.after(0, on_error)
                
        threading.Thread(target=test_output, daemon=True).start()
        
    def _toggle_monitoring(self):
        """Toggle audio monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.widgets['monitor_toggle'].configure(text="⏹️ Stop Monitoring", style='Danger.TButton')
            self._start_monitoring()
        else:
            self.monitoring_active = False
            self.widgets['monitor_toggle'].configure(text="▶️ Start Monitoring", style='Accent.TButton')
            self._stop_monitoring()
            
    def _start_monitoring(self):
        """Start audio level monitoring"""
        def monitor():
            while self.monitoring_active:
                try:
                    # Simulate audio levels (replace with actual audio capture)
                    import random
                    input_level = random.randint(0, 100) if self.current_input_device else 0
                    output_level = random.randint(0, 100) if self.current_output_device else 0
                    
                    def update_ui():
                        if self.monitoring_active:
                            self.widgets['input_level_var'].set(input_level)
                            self.widgets['output_level_var'].set(output_level)
                            
                            # Update status indicators
                            if input_level > 50:
                                self.widgets['input_status'].configure(text="🔴 Recording")
                            elif input_level > 10:
                                self.widgets['input_status'].configure(text="🟡 Active")
                            else:
                                self.widgets['input_status'].configure(text="🎤 Ready")
                                
                            if output_level > 50:
                                self.widgets['output_status'].configure(text="🟢 Playing")
                            elif output_level > 10:
                                self.widgets['output_status'].configure(text="🟡 Active")  
                            else:
                                self.widgets['output_status'].configure(text="🔊 Ready")
                                
                    self.frame.after(0, update_ui)
                    
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    
                time.sleep(0.1)
                
        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()
        
    def _stop_monitoring(self):
        """Stop audio level monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread = None
            
        # Reset UI
        self.widgets['input_level_var'].set(0)
        self.widgets['output_level_var'].set(0)
        self.widgets['input_status'].configure(text="🎤 Ready")
        self.widgets['output_status'].configure(text="🔊 Ready")
        
    def _test_audio_system(self):
        """Test entire audio system"""
        self.widgets['test_audio_btn'].configure(text="Testing...", state='disabled')
        
        def test_system():
            try:
                if hasattr(self.app_controller, 'backend_client'):
                    result = self.app_controller.backend_client.get_audio_status()
                    
                    def on_complete():
                        self.widgets['test_audio_btn'].configure(
                            text="🔊 Test Audio System", state='normal')
                        
                        if result.get('status') != 'error':
                            self.show_success("Audio system test completed successfully")
                            # Show detailed results
                            details = f"Input devices: {len(self.input_devices)}\n"
                            details += f"Output devices: {len(self.output_devices)}\n"
                            details += f"Audio engine: {result.get('audio_engine', 'Unknown')}"
                            self.show_info(f"Audio System Details:\n{details}")
                        else:
                            self.show_error(f"Audio system test failed: {result.get('message', 'Unknown error')}")
                            
                    self.frame.after(0, on_complete)
                else:
                    time.sleep(1)
                    def on_complete():
                        self.widgets['test_audio_btn'].configure(
                            text="🔊 Test Audio System", state='normal')
                        self.show_success("Audio system test completed (offline mode)")
                    self.frame.after(0, on_complete)
                    
            except Exception as e:
                def on_error():
                    self.widgets['test_audio_btn'].configure(
                        text="🔊 Test Audio System", state='normal')
                    self.show_error(f"System test failed: {e}")
                self.frame.after(0, on_error)
                
        threading.Thread(target=test_system, daemon=True).start()
        
    def _open_advanced_settings(self):
        """Open advanced audio settings dialog"""
        self.show_info("Advanced audio settings dialog would open here")
        # TODO: Implement advanced settings dialog
        
    def _run_audio_diagnostics(self):
        """Run comprehensive audio diagnostics"""
        self.widgets['diagnostics_btn'].configure(text="Running...", state='disabled')
        
        def run_diagnostics():
            try:
                # Collect diagnostic information
                diagnostics = {
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'input_devices': len(self.input_devices),
                    'output_devices': len(self.output_devices),
                    'current_input': self.current_input_device['name'] if self.current_input_device else None,
                    'current_output': self.current_output_device['name'] if self.current_output_device else None,
                    'monitoring_active': self.monitoring_active
                }
                
                def on_complete():
                    self.widgets['diagnostics_btn'].configure(
                        text="🔍 Audio Diagnostics", state='normal')
                    
                    # Show diagnostics report
                    report = "Audio Diagnostics Report\n"
                    report += "=" * 30 + "\n"
                    for key, value in diagnostics.items():
                        report += f"{key.replace('_', ' ').title()}: {value}\n"
                    
                    self.show_info(report)
                    
                self.frame.after(0, on_complete)
                
            except Exception as e:
                def on_error():
                    self.widgets['diagnostics_btn'].configure(
                        text="🔍 Audio Diagnostics", state='normal')
                    self.show_error(f"Diagnostics failed: {e}")
                self.frame.after(0, on_error)
                
        threading.Thread(target=run_diagnostics, daemon=True).start()
        
    def refresh_devices(self):
        """Refresh device lists from backend"""
        try:
            if hasattr(self.app_controller, 'backend_client'):
                def fetch_devices():
                    try:
                        result = self.app_controller.backend_client.get_audio_devices()
                        
                        def on_success():
                            if 'devices' in result:
                                devices = result['devices']
                                
                                # Separate input and output devices
                                self.input_devices = [d for d in devices.get('input', [])]
                                self.output_devices = [d for d in devices.get('output', [])]
                                
                                # Update UI
                                self._refresh_device_lists()
                                self.show_success(f"Loaded {len(self.input_devices)} input and {len(self.output_devices)} output devices")
                            else:
                                self._load_fallback_devices()
                                
                        def on_error(error_msg):
                            self.show_error(f"Failed to load devices: {error_msg}")
                            self._load_fallback_devices()
                            
                        if result.get('status') != 'error':
                            self.frame.after(0, on_success)
                        else:
                            self.frame.after(0, lambda: on_error(result.get('message', 'Unknown error')))
                            
                    except Exception as e:
                        self.frame.after(0, lambda: on_error(str(e)))
                        
                threading.Thread(target=fetch_devices, daemon=True).start()
            else:
                self._load_fallback_devices()
                
        except Exception as e:
            logger.error(f"Error refreshing devices: {e}")
            self._load_fallback_devices()
            
    def _load_fallback_devices(self):
        """Load fallback devices for demo purposes"""
        self.input_devices = [
            {'index': 0, 'name': 'Built-in Microphone', 'default_sample_rate': 44100, 'max_input_channels': 1},
            {'index': 1, 'name': 'USB Headset Microphone', 'default_sample_rate': 48000, 'max_input_channels': 1},
            {'index': 2, 'name': 'Virtual Audio Cable', 'default_sample_rate': 44100, 'max_input_channels': 2}
        ]
        
        self.output_devices = [
            {'index': 0, 'name': 'Built-in Speakers', 'default_sample_rate': 44100, 'max_output_channels': 2},
            {'index': 1, 'name': 'USB Headset Speakers', 'default_sample_rate': 48000, 'max_output_channels': 2},
            {'index': 2, 'name': 'Virtual Audio Cable', 'default_sample_rate': 44100, 'max_output_channels': 2}
        ]
        
        self._refresh_device_lists()
        
    def _refresh_device_lists(self):
        """Refresh device listboxes"""
        # Clear existing lists
        self.widgets['input_listbox'].delete(0, tk.END)
        self.widgets['output_listbox'].delete(0, tk.END)
        
        # Add input devices
        for i, device in enumerate(self.input_devices):
            name = device.get('name', f'Device {i}')
            self.widgets['input_listbox'].insert(tk.END, name)
            
        # Add output devices
        for i, device in enumerate(self.output_devices):
            name = device.get('name', f'Device {i}')
            self.widgets['output_listbox'].insert(tk.END, name)
            
        # Select first devices by default
        if self.input_devices:
            self.widgets['input_listbox'].selection_set(0)
            self._set_input_device(self.input_devices[0])
            
        if self.output_devices:
            self.widgets['output_listbox'].selection_set(0)
            self._set_output_device(self.output_devices[0])
            
    def cleanup(self):
        """Cleanup when panel is destroyed"""
        self._stop_monitoring()
        super().cleanup()
        
    def update_state(self, state: Dict[str, Any]):
        """Update audio devices state"""
        if 'refresh_devices' in state and state['refresh_devices']:
            self.refresh_devices()
            
        if 'volume' in state:
            self.widgets['volume_var'].set(state['volume'])
            
    def get_state(self) -> Dict[str, Any]:
        """Get current audio devices state"""
        return {
            'input_device_count': len(self.input_devices),
            'output_device_count': len(self.output_devices),
            'current_input': self.current_input_device['name'] if self.current_input_device else None,
            'current_output': self.current_output_device['name'] if self.current_output_device else None,
            'volume': self.widgets['volume_var'].get(),
            'monitoring_active': self.monitoring_active
        }
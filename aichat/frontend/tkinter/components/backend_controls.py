"""
Backend Controls Panel - Backend process management
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
import subprocess
import threading
import time
import logging
import os
import signal
import psutil

from .base import PanelComponent
from ..theme import theme

logger = logging.getLogger(__name__)


class BackendControlsPanel(PanelComponent):
    """Panel for backend process management"""
    
    def __init__(self, parent: tk.Widget, app_controller=None):
        self.backend_process = None
        self.backend_pid = None
        self.auto_start = True
        self.backend_url = "http://localhost:8765"
        self.is_monitoring = False
        super().__init__(parent, "Backend Control", app_controller)
        
    def _setup_component(self):
        """Setup backend controls"""
        # Process status
        status_frame = ttk.Frame(self.frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.create_label(status_frame, "Status:", style='Heading.TLabel').pack(anchor=tk.W)
        
        status_display_frame = ttk.Frame(status_frame)
        status_display_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.widgets['status_label'] = self.create_label(
            status_display_frame, "Stopped", style='Normal.TLabel')
        self.widgets['status_label'].pack(side=tk.LEFT)
        
        self.widgets['pid_label'] = self.create_label(
            status_display_frame, "", style='Normal.TLabel')
        self.widgets['pid_label'].pack(side=tk.RIGHT)
        
        # Control buttons
        control_frame = ttk.Frame(self.frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.widgets['start_button'] = self.create_button(
            control_frame, "▶️ Start Backend", 
            command=self.start_backend, style='Success.TButton')
        self.widgets['start_button'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['stop_button'] = self.create_button(
            control_frame, "⏹️ Stop Backend", 
            command=self.stop_backend, style='Warning.TButton')
        self.widgets['stop_button'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['restart_button'] = self.create_button(
            control_frame, "🔄 Restart", 
            command=self.restart_backend)
        self.widgets['restart_button'].pack(side=tk.LEFT)
        
        # Configuration
        config_frame = ttk.Frame(self.frame)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.create_label(config_frame, "Configuration:", style='Heading.TLabel').pack(anchor=tk.W)
        
        url_frame = ttk.Frame(config_frame)
        url_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.create_label(url_frame, "URL:", style='Normal.TLabel').pack(side=tk.LEFT)
        
        self.widgets['url_entry'] = tk.Entry(
            url_frame, font=theme.fonts.body,
            bg=theme.colors.bg_tertiary, fg=theme.colors.text_primary,
            insertbackground=theme.colors.text_primary,
            relief='solid', bd=2)
        self.widgets['url_entry'].pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        self.widgets['url_entry'].insert(0, self.backend_url)
        
        # Auto-start checkbox
        auto_frame = ttk.Frame(config_frame)
        auto_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.widgets['auto_start_var'] = tk.BooleanVar(value=self.auto_start)
        self.widgets['auto_start_check'] = ttk.Checkbutton(
            auto_frame, text="Auto-start backend on GUI launch",
            variable=self.widgets['auto_start_var'],
            command=self._on_auto_start_change)
        self.widgets['auto_start_check'].pack(anchor=tk.W)
        
        # Process info
        info_frame = ttk.Frame(self.frame)
        info_frame.pack(fill=tk.X)
        
        self.create_label(info_frame, "Process Info:", style='Heading.TLabel').pack(anchor=tk.W)
        
        self.widgets['info_text'] = tk.Text(
            info_frame, height=6, width=50,
            bg=theme.colors.bg_primary, fg=theme.colors.text_secondary,
            font=theme.fonts.caption, relief='solid', bd=2,
            state=tk.DISABLED)
        self.widgets['info_text'].pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Initialize UI and start monitoring
        self._update_ui_state()
        self._start_process_monitoring()
        
        # Auto-start if enabled
        if self.auto_start:
            self.frame.after(1000, self.start_backend)
            
    def _on_auto_start_change(self):
        """Handle auto-start setting change"""
        self.auto_start = self.widgets['auto_start_var'].get()
        
    def start_backend(self):
        """Start the backend process"""
        if self.backend_process and self._is_process_running():
            self.show_info("Backend is already running")
            return
            
        try:
            self.widgets['start_button'].configure(state='disabled', text="Starting...")
            self.show_info("Starting backend...")
            
            # Start backend process
            cmd = ["aichat", "backend", "--host", "localhost", "--port", "8765", "--reload"]
            
            self.backend_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.backend_pid = self.backend_process.pid
            
            # Wait a moment for process to initialize
            threading.Thread(target=self._wait_for_startup, daemon=True).start()
            
        except Exception as e:
            self.show_error(f"Failed to start backend: {e}")
            self._update_ui_state()
            
    def _wait_for_startup(self):
        """Wait for backend to start and update UI"""
        time.sleep(2)  # Give process time to start
        
        def update_ui():
            if self._is_process_running():
                self.show_success(f"Backend started (PID: {self.backend_pid})")
                self.emit_event('backend_started', self.backend_pid)
            else:
                self.show_error("Backend failed to start")
            self._update_ui_state()
            
        self.frame.after(0, update_ui)
        
    def stop_backend(self):
        """Stop the backend process"""
        if not self.backend_process or not self._is_process_running():
            self.show_info("Backend is not running")
            return
            
        try:
            self.widgets['stop_button'].configure(state='disabled', text="Stopping...")
            self.show_info("Stopping backend...")
            
            # Try graceful shutdown first
            if os.name == 'nt':  # Windows
                self.backend_process.terminate()
            else:  # Unix-like
                self.backend_process.send_signal(signal.SIGTERM)
                
            # Wait for graceful shutdown
            try:
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                self.backend_process.kill()
                self.backend_process.wait()
                
            self.backend_process = None
            self.backend_pid = None
            
            self.show_success("Backend stopped")
            self.emit_event('backend_stopped')
            
        except Exception as e:
            self.show_error(f"Failed to stop backend: {e}")
        finally:
            self._update_ui_state()
            
    def restart_backend(self):
        """Restart the backend process"""
        self.show_info("Restarting backend...")
        
        def restart_sequence():
            if self.backend_process and self._is_process_running():
                self.stop_backend()
                time.sleep(2)  # Wait for shutdown
            self.start_backend()
            
        threading.Thread(target=restart_sequence, daemon=True).start()
        
    def _is_process_running(self) -> bool:
        """Check if backend process is running"""
        if not self.backend_process:
            return False
            
        try:
            # Check if process exists and is running
            if self.backend_pid:
                return psutil.pid_exists(self.backend_pid)
            return self.backend_process.poll() is None
        except:
            return False
            
    def _start_process_monitoring(self):
        """Start monitoring backend process"""
        def monitor():
            self.is_monitoring = True
            while self.is_monitoring:
                self._update_process_info()
                time.sleep(2)
                
        threading.Thread(target=monitor, daemon=True).start()
        
    def _update_process_info(self):
        """Update process information display"""
        def update_ui():
            try:
                info_lines = []
                
                if self._is_process_running() and self.backend_pid:
                    try:
                        process = psutil.Process(self.backend_pid)
                        info_lines.extend([
                            f"PID: {self.backend_pid}",
                            f"Status: {process.status()}",
                            f"CPU: {process.cpu_percent():.1f}%",
                            f"Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB",
                            f"Threads: {process.num_threads()}",
                            f"Created: {time.strftime('%H:%M:%S', time.localtime(process.create_time()))}"
                        ])
                    except:
                        info_lines.append("Process information unavailable")
                else:
                    info_lines.append("Backend not running")
                    
                # Update info display
                if hasattr(self, 'widgets') and 'info_text' in self.widgets:
                    self.widgets['info_text'].configure(state=tk.NORMAL)
                    self.widgets['info_text'].delete(1.0, tk.END)
                    self.widgets['info_text'].insert(1.0, "\n".join(info_lines))
                    self.widgets['info_text'].configure(state=tk.DISABLED)
            except RuntimeError:
                # GUI is being destroyed, stop monitoring
                self.is_monitoring = False
            except Exception as e:
                logger.error(f"Error updating process info: {e}")
            
        try:
            if hasattr(self, 'frame') and self.frame.winfo_exists():
                self.frame.after(0, update_ui)
        except (RuntimeError, tk.TclError):
            # GUI is being destroyed, stop monitoring
            self.is_monitoring = False
        
    def _update_ui_state(self):
        """Update UI based on current state"""
        is_running = self._is_process_running()
        
        # Update status
        if is_running:
            self.widgets['status_label'].configure(
                text="Running ✅", foreground=theme.colors.success)
            if self.backend_pid:
                self.widgets['pid_label'].configure(text=f"PID: {self.backend_pid}")
        else:
            self.widgets['status_label'].configure(
                text="Stopped ❌", foreground=theme.colors.danger)
            self.widgets['pid_label'].configure(text="")
            
        # Update button states
        self.widgets['start_button'].configure(
            state='disabled' if is_running else 'normal',
            text="▶️ Start Backend")
        self.widgets['stop_button'].configure(
            state='normal' if is_running else 'disabled',
            text="⏹️ Stop Backend")
        self.widgets['restart_button'].configure(
            state='normal' if is_running else 'disabled')
            
    def update_state(self, state: Dict[str, Any]):
        """Update backend controls state"""
        if 'backend_url' in state:
            self.backend_url = state['backend_url']
            self.widgets['url_entry'].delete(0, tk.END)
            self.widgets['url_entry'].insert(0, self.backend_url)
            
        if 'auto_start' in state:
            self.auto_start = state['auto_start']
            self.widgets['auto_start_var'].set(self.auto_start)
            
    def get_state(self) -> Dict[str, Any]:
        """Get current backend controls state"""
        return {
            'backend_url': self.widgets['url_entry'].get(),
            'auto_start': self.widgets['auto_start_var'].get(),
            'is_running': self._is_process_running(),
            'backend_pid': self.backend_pid
        }
        
    def cleanup(self):
        """Cleanup when component is destroyed"""
        self.is_monitoring = False
        if self.backend_process and self._is_process_running():
            try:
                self.backend_process.terminate()
            except:
                pass
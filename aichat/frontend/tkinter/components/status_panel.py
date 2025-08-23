"""
Status Panel Component - Shows system status and connection info
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any
import time
import requests
import logging

from .base import PanelComponent
from ..theme import theme
from ..utils import format_time_duration

logger = logging.getLogger(__name__)


class StatusPanel(PanelComponent):
    """Panel showing system status and backend connection"""
    
    def __init__(self, parent: tk.Widget, app_controller=None):
        self.backend_url = "http://localhost:8765"
        self.last_check = None
        self.uptime_start = time.time()
        super().__init__(parent, "System Status", app_controller)
        
    def _setup_component(self):
        """Setup the status panel"""
        # Create status grid
        status_frame = ttk.Frame(self.frame)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Backend status
        self.create_label(status_frame, "Backend:", style='Heading.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.widgets['backend_status'] = self.create_label(
            status_frame, "Checking...", style='Normal.TLabel')
        self.widgets['backend_status'].grid(row=0, column=1, sticky=tk.W)
        
        # Connection status  
        self.create_label(status_frame, "Connection:", style='Heading.TLabel').grid(
            row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.widgets['connection_status'] = self.create_label(
            status_frame, "Disconnected", style='Normal.TLabel')
        self.widgets['connection_status'].grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # Last check time
        self.create_label(status_frame, "Last Check:", style='Heading.TLabel').grid(
            row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.widgets['last_check'] = self.create_label(
            status_frame, "Never", style='Normal.TLabel')
        self.widgets['last_check'].grid(row=2, column=1, sticky=tk.W, pady=(5, 0))
        
        # Uptime
        self.create_label(status_frame, "GUI Uptime:", style='Heading.TLabel').grid(
            row=3, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.widgets['uptime'] = self.create_label(
            status_frame, "0s", style='Normal.TLabel')
        self.widgets['uptime'].grid(row=3, column=1, sticky=tk.W, pady=(5, 0))
        
        # Audio status
        self.create_label(status_frame, "Audio:", style='Heading.TLabel').grid(
            row=4, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.widgets['audio_status'] = self.create_label(
            status_frame, self._get_audio_status(), style='Normal.TLabel')
        self.widgets['audio_status'].grid(row=4, column=1, sticky=tk.W, pady=(5, 0))
        
        # Control buttons
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.widgets['refresh_btn'] = self.create_button(
            button_frame, "🔄 Refresh", command=self.refresh_status)
        self.widgets['refresh_btn'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['test_connection_btn'] = self.create_button(
            button_frame, "🔗 Test Connection", command=self.test_connection)
        self.widgets['test_connection_btn'].pack(side=tk.LEFT)
        
        # Initial status check
        self.refresh_status()
        
    def _get_audio_status(self) -> str:
        """Get audio system status"""
        try:
            import pyaudio
            return "Available"
        except ImportError:
            return "Not Available (PyAudio missing)"
        except Exception as e:
            return f"Error: {e}"
            
    def set_backend_url(self, url: str):
        """Set backend URL"""
        self.backend_url = url
        self.refresh_status()
        
    def refresh_status(self):
        """Refresh all status information"""
        self._check_backend_status()
        self._update_uptime()
        
    def _check_backend_status(self):
        """Check backend connection status"""
        try:
            response = requests.get(f"{self.backend_url}/api/system/status", timeout=3)
            
            if response.status_code == 200:
                self.widgets['backend_status'].configure(text="Running ✅")
                self.widgets['connection_status'].configure(text="Connected ✅")
                
                # Show backend info if available
                try:
                    data = response.json()
                    uptime = data.get('uptime', 0)
                    uptime_str = format_time_duration(uptime)
                    self.widgets['backend_status'].configure(
                        text=f"Running ✅ (Up: {uptime_str})")
                except:
                    pass
                    
            else:
                self.widgets['backend_status'].configure(
                    text=f"Error ❌ (HTTP {response.status_code})")
                self.widgets['connection_status'].configure(text="Error ❌")
                
        except requests.exceptions.ConnectionError:
            self.widgets['backend_status'].configure(text="Not Running ❌")
            self.widgets['connection_status'].configure(text="No Connection ❌")
        except requests.exceptions.Timeout:
            self.widgets['backend_status'].configure(text="Timeout ⏰")
            self.widgets['connection_status'].configure(text="Timeout ⏰")
        except Exception as e:
            self.widgets['backend_status'].configure(text="Unknown ❓")
            self.widgets['connection_status'].configure(text=f"Error: {e}")
            
        # Update last check time
        self.last_check = time.time()
        check_time = time.strftime("%H:%M:%S", time.localtime(self.last_check))
        self.widgets['last_check'].configure(text=check_time)
        
    def _update_uptime(self):
        """Update GUI uptime display"""
        uptime_seconds = time.time() - self.uptime_start
        uptime_str = format_time_duration(uptime_seconds)
        self.widgets['uptime'].configure(text=uptime_str)
        
    def test_connection(self):
        """Test backend connection with detailed feedback"""
        self.widgets['test_connection_btn'].configure(text="Testing...", state='disabled')
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/api/system/status", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                self.show_success(f"Connection successful! ({response_time:.0f}ms)")
                
                # Test additional endpoints
                endpoints = [
                    "/api/chat/characters",
                    "/api/voice/audio/status"
                ]
                
                results = []
                for endpoint in endpoints:
                    try:
                        test_response = requests.get(f"{self.backend_url}{endpoint}", timeout=5)
                        status = "✅" if test_response.status_code == 200 else "❌"
                        results.append(f"{endpoint}: {status}")
                    except:
                        results.append(f"{endpoint}: ❌")
                
                detail_msg = "\\n".join(results)
                self.show_info(f"Endpoint tests:\\n{detail_msg}")
                
            else:
                self.show_error(f"Connection failed: HTTP {response.status_code}")
                
        except Exception as e:
            self.show_error(f"Connection test failed: {e}")
        finally:
            self.widgets['test_connection_btn'].configure(
                text="🔗 Test Connection", state='normal')
            
    def update_state(self, state: Dict[str, Any]):
        """Update status panel state"""
        if 'backend_url' in state:
            self.set_backend_url(state['backend_url'])
            
        if 'auto_refresh' in state and state['auto_refresh']:
            self.refresh_status()
            
    def get_state(self) -> Dict[str, Any]:
        """Get current status panel state"""
        return {
            'backend_url': self.backend_url,
            'last_check': self.last_check,
            'uptime': time.time() - self.uptime_start
        }
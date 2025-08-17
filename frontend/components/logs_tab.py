"""
Event logs tab component
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional, Dict, Any
import requests
import logging
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from .base_component import BaseComponent

logger = logging.getLogger(__name__)


class LogsTab(BaseComponent):
    """Event logs tab"""
    
    def __init__(self, parent: tk.Widget, main_app: Optional[Any] = None):
        super().__init__(parent, main_app)
        self.api_base_url = f"http://{main_app.settings.api_host}:{main_app.settings.api_port}"
        
    def create(self):
        """Create logs tab UI"""
        self.frame = ttk.Frame(self.parent)
        
        # Log controls
        controls_frame = ttk.Frame(self.frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_check = ttk.Checkbutton(controls_frame, text="Auto Refresh", variable=self.auto_refresh_var)
        auto_refresh_check.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(controls_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.log_filter_var = tk.StringVar(value="all")
        log_filter_combo = ttk.Combobox(controls_frame, textvariable=self.log_filter_var, width=15)
        log_filter_combo['values'] = ["all", "INFO", "WARNING", "ERROR", "CRITICAL"]
        log_filter_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        refresh_logs_button = ttk.Button(controls_frame, text="Refresh Logs", command=self.refresh_logs)
        refresh_logs_button.pack(side=tk.RIGHT)
        
        # Log display
        self.logs_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, height=25)
        self.logs_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Clear logs button
        clear_button = ttk.Button(self.frame, text="Clear Logs", command=self.clear_logs)
        clear_button.pack(pady=5)
        
        # Store widgets
        self.add_widget("auto_refresh_var", self.auto_refresh_var)
        self.add_widget("log_filter_var", self.log_filter_var)
        self.add_widget("logs_text", self.logs_text)
    
    def refresh_logs(self):
        """Refresh event logs"""
        try:
            response = requests.get(f"{self.api_base_url}/api/system/logs")
            if response.status_code == 200:
                logs = response.json().get("logs", [])
                
                # Clear existing logs
                self.logs_text.delete(1.0, tk.END)
                
                # Add logs
                for log in logs:
                    severity = log.get("severity", "INFO")
                    message = log.get("message", "")
                    timestamp = log.get("timestamp", "")[:19] if log.get("timestamp") else ""
                    
                    log_line = f"[{timestamp}] [{severity}] {message}\n"
                    self.logs_text.insert(tk.END, log_line)
                
                # Auto-scroll to bottom
                self.logs_text.see(tk.END)
        except Exception as e:
            logger.error(f"Error refreshing logs: {e}")
    
    def clear_logs(self):
        """Clear event logs"""
        try:
            response = requests.post(f"{self.api_base_url}/api/system/logs/clear")
            if response.status_code == 200:
                self.logs_text.delete(1.0, tk.END)
                self.add_log("Logs cleared")
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
    
    def add_log(self, message: str):
        """Add log message"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if self.main_app else ""
        log_line = f"[{timestamp}] {message}\n"
        self.logs_text.insert(tk.END, log_line)
        self.logs_text.see(tk.END)
    
    def refresh(self):
        """Refresh component data"""
        self.refresh_logs()
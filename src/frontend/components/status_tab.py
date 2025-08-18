"""
Status monitoring tab component
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
import requests
import logging
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from .base_component import BaseComponent

logger = logging.getLogger(__name__)


class StatusTab(BaseComponent):
    """System status monitoring tab"""
    
    def __init__(self, parent: tk.Widget, main_app: Optional[Any] = None):
        super().__init__(parent, main_app)
        self.api_base_url = f"http://{main_app.settings.api_host}:{main_app.settings.api_port}"
        
    def create(self):
        """Create status tab UI"""
        self.frame = ttk.Frame(self.parent)
        
        # Connection status
        conn_frame = ttk.LabelFrame(self.frame, text="Connection Status")
        conn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.connection_label = ttk.Label(conn_frame, text="Connecting...", foreground="orange")
        self.connection_label.pack(pady=5)
        
        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.pack(pady=5)
        
        # System status
        system_frame = ttk.LabelFrame(self.frame, text="System Status")
        system_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for system status
        columns = ("Metric", "Value")
        self.status_tree = ttk.Treeview(system_frame, columns=columns, show="headings", height=10)
        self.status_tree.heading("Metric", text="Metric")
        self.status_tree.heading("Value", text="Value")
        self.status_tree.column("Metric", width=200)
        self.status_tree.column("Value", width=300)
        
        # Add scrollbar
        status_scrollbar = ttk.Scrollbar(system_frame, orient=tk.VERTICAL, command=self.status_tree.yview)
        self.status_tree.configure(yscrollcommand=status_scrollbar.set)
        
        self.status_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Refresh button
        refresh_button = ttk.Button(self.frame, text="Refresh Status", command=self.refresh_status)
        refresh_button.pack(pady=5)
        
        # Store widgets
        self.add_widget("connection_label", self.connection_label)
        self.add_widget("connect_button", self.connect_button)
        self.add_widget("status_tree", self.status_tree)
    
    def refresh_status(self):
        """Refresh system status"""
        try:
            response = requests.get(f"{self.api_base_url}/api/system/status")
            if response.status_code == 200:
                status_data = response.json()
                self.update_system_status_display(status_data)
        except Exception as e:
            logger.error(f"Error refreshing status: {e}")
    
    def update_system_status_display(self, status_data: Dict[str, Any]):
        """Update system status display"""
        # Clear existing items
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        
        # Add status items
        self.status_tree.insert("", "end", values=("Status", status_data.get("status", "unknown")))
        self.status_tree.insert("", "end", values=("Uptime", f"{status_data.get('uptime', 0):.2f}s"))
        self.status_tree.insert("", "end", values=("CPU Usage", f"{status_data.get('cpu_usage', 0):.1f}%"))
        self.status_tree.insert("", "end", values=("Memory Usage", f"{status_data.get('memory_usage', 0):.1f}%"))
        self.status_tree.insert("", "end", values=("Disk Usage", f"{status_data.get('disk_usage', {}).get('percent', 0):.1f}%"))
        
        # Services status
        services = status_data.get("services", {})
        for service, status in services.items():
            self.status_tree.insert("", "end", values=(f"Service: {service}", status))
    
    def toggle_connection(self):
        """Toggle WebSocket connection"""
        if self.main_app:
            self.main_app.toggle_connection()
    
    def update_connection_status(self):
        """Update connection status display"""
        if not self.main_app:
            return
            
        if self.main_app.connected:
            self.connection_label.config(text="Connected", foreground="green")
            self.connect_button.config(text="Disconnect", command=self.toggle_connection)
        else:
            self.connection_label.config(text="Disconnected", foreground="red")
            self.connect_button.config(text="Connect", command=self.toggle_connection)
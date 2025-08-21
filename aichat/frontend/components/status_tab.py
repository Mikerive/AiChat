"""
Status monitoring tab component
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, Optional

import requests

# Third-party imports
import tkinter as tk
from tkinter import ttk

# Local imports
from .base_component import BaseComponent

logger = logging.getLogger(__name__)


class StatusTab(BaseComponent):
    """System status monitoring tab"""

    def __init__(self, parent: tk.Widget, main_app: Optional[Any] = None):
        super().__init__(parent, main_app)
        self.api_base_url = (
            f"http://{main_app.settings.api_host}:{main_app.settings.api_port}"
        )

    def create(self):
        """Create status tab UI with manual service control"""
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Service Control Panel
        control_frame = ttk.LabelFrame(self.frame, text="Service Control")
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Backend Service Controls
        backend_frame = ttk.Frame(control_frame)
        backend_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(backend_frame, text="Backend Server:").pack(
            side=tk.LEFT, padx=(0, 10)
        )
        self.backend_status_label = ttk.Label(
            backend_frame, text="Stopped", foreground="red"
        )
        self.backend_status_label.pack(side=tk.LEFT, padx=(0, 10))

        self.start_backend_btn = ttk.Button(
            backend_frame, text="Start Backend", command=self.start_backend
        )
        self.start_backend_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_backend_btn = ttk.Button(
            backend_frame,
            text="Stop Backend",
            command=self.stop_backend,
            state=tk.DISABLED,
        )
        self.stop_backend_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.check_backend_btn = ttk.Button(
            backend_frame, text="Check Status", command=self.check_backend_status
        )
        self.check_backend_btn.pack(side=tk.LEFT)

        # WebSocket Connection Controls
        ws_frame = ttk.Frame(control_frame)
        ws_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(ws_frame, text="WebSocket:").pack(side=tk.LEFT, padx=(0, 10))
        self.ws_status_label = ttk.Label(
            ws_frame, text="Disconnected", foreground="red"
        )
        self.ws_status_label.pack(side=tk.LEFT, padx=(0, 10))

        self.connect_ws_btn = ttk.Button(
            ws_frame, text="Connect WS", command=self.connect_websocket
        )
        self.connect_ws_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.disconnect_ws_btn = ttk.Button(
            ws_frame,
            text="Disconnect WS",
            command=self.disconnect_websocket,
            state=tk.DISABLED,
        )
        self.disconnect_ws_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Configuration Status
        config_frame = ttk.LabelFrame(self.frame, text="Configuration Status")
        config_frame.pack(fill=tk.X, padx=5, pady=5)

        config_tree_frame = ttk.Frame(config_frame)
        config_tree_frame.pack(fill=tk.X, padx=5, pady=5)

        columns = ("Setting", "Status", "Value")
        self.config_tree = ttk.Treeview(
            config_tree_frame, columns=columns, show="headings", height=6
        )
        self.config_tree.heading("Setting", text="Setting")
        self.config_tree.heading("Status", text="Status")
        self.config_tree.heading("Value", text="Value")
        self.config_tree.column("Setting", width=200)
        self.config_tree.column("Status", width=100)
        self.config_tree.column("Value", width=300)
        self.config_tree.pack(fill=tk.X)

        # System Metrics
        metrics_frame = ttk.LabelFrame(self.frame, text="System Metrics")
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        metrics_tree_frame = ttk.Frame(metrics_frame)
        metrics_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("Metric", "Value")
        self.metrics_tree = ttk.Treeview(
            metrics_tree_frame, columns=columns, show="headings"
        )
        self.metrics_tree.heading("Metric", text="Metric")
        self.metrics_tree.heading("Value", text="Value")
        self.metrics_tree.column("Metric", width=250)
        self.metrics_tree.column("Value", width=350)

        # Add scrollbar for metrics
        metrics_scrollbar = ttk.Scrollbar(
            metrics_tree_frame, orient=tk.VERTICAL, command=self.metrics_tree.yview
        )
        self.metrics_tree.configure(yscrollcommand=metrics_scrollbar.set)

        self.metrics_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        metrics_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Control buttons
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            button_frame, text="Refresh All", command=self.refresh_all_status
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            button_frame, text="Test Backend API", command=self.test_backend_api
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="View Logs", command=self.view_logs).pack(
            side=tk.LEFT
        )

        # Initialize status display
        self.update_config_status()
        self.update_service_status()

        # Store widgets
        self.add_widget("backend_status_label", self.backend_status_label)
        self.add_widget("ws_status_label", self.ws_status_label)
        self.add_widget("config_tree", self.config_tree)
        self.add_widget("metrics_tree", self.metrics_tree)

    def start_backend(self):
        """Start the backend server"""
        if self.main_app:
            self.main_app.manual_start_backend()
            self.update_service_status()

    def stop_backend(self):
        """Stop the backend server"""
        if self.main_app:
            self.main_app.stop_backend()
            self.update_service_status()

    def check_backend_status(self):
        """Check if backend is running"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=2)
            if response.status_code == 200:
                self.backend_status_label.config(text="Running", foreground="green")
                self.start_backend_btn.config(state=tk.DISABLED)
                self.stop_backend_btn.config(state=tk.NORMAL)
                self.main_app.add_log("Backend server is responding")
            else:
                self.backend_status_label.config(text="Error", foreground="red")
                self.main_app.add_log(
                    f"Backend responded with status: {response.status_code}"
                )
        except Exception as e:
            self.backend_status_label.config(text="Stopped", foreground="red")
            self.start_backend_btn.config(state=tk.NORMAL)
            self.stop_backend_btn.config(state=tk.DISABLED)
            self.main_app.add_log(f"Backend check failed: {e}")

    def connect_websocket(self):
        """Connect WebSocket"""
        if self.main_app and hasattr(self.main_app, "ws_handler"):
            self.main_app.ws_handler.start()
            self.main_app.add_log("WebSocket connection initiated")
            self.update_service_status()

    def disconnect_websocket(self):
        """Disconnect WebSocket"""
        if self.main_app and hasattr(self.main_app, "ws_handler"):
            self.main_app.ws_handler.disconnect()
            self.main_app.connected = False
            self.main_app.add_log("WebSocket disconnected")
            self.update_service_status()

    def update_config_status(self):
        """Update configuration status display"""
        # Clear existing items
        for item in self.config_tree.get_children():
            self.config_tree.delete(item)

        # Check configuration items
        settings = self.main_app.settings

        # API Configuration
        self.config_tree.insert(
            "",
            "end",
            values=("API Host", "OK", f"{settings.api_host}:{settings.api_port}"),
        )

        # OpenRouter API Key
        if settings.openrouter_api_key:
            key_display = (
                f"***{settings.openrouter_api_key[-4:]}"
                if len(settings.openrouter_api_key) > 4
                else "***"
            )
            self.config_tree.insert(
                "", "end", values=("OpenRouter API Key", "✓ Configured", key_display)
            )
        else:
            self.config_tree.insert(
                "", "end", values=("OpenRouter API Key", "✗ Missing", "Not configured")
            )

        # Models
        self.config_tree.insert(
            "", "end", values=("Whisper Model", "OK", settings.whisper_model)
        )
        self.config_tree.insert(
            "", "end", values=("Piper Model Path", "OK", str(settings.piper_model_path))
        )

        # Database
        self.config_tree.insert(
            "", "end", values=("Database URL", "OK", settings.database_url)
        )

        # Character
        self.config_tree.insert(
            "",
            "end",
            values=(
                "Character",
                "OK",
                f"{settings.character_name} ({settings.character_profile})",
            ),
        )

    def update_service_status(self):
        """Update service status indicators"""
        # Update WebSocket status
        if self.main_app and self.main_app.connected:
            self.ws_status_label.config(text="Connected", foreground="green")
            self.connect_ws_btn.config(state=tk.DISABLED)
            self.disconnect_ws_btn.config(state=tk.NORMAL)
        else:
            self.ws_status_label.config(text="Disconnected", foreground="red")
            self.connect_ws_btn.config(state=tk.NORMAL)
            self.disconnect_ws_btn.config(state=tk.DISABLED)

        # Update backend status
        if self.main_app and self.main_app.is_backend_running():
            self.backend_status_label.config(text="Running", foreground="green")
            self.start_backend_btn.config(state=tk.DISABLED)
            self.stop_backend_btn.config(state=tk.NORMAL)
        else:
            self.backend_status_label.config(text="Stopped", foreground="red")
            self.start_backend_btn.config(state=tk.NORMAL)
            self.stop_backend_btn.config(state=tk.DISABLED)

    def refresh_all_status(self):
        """Refresh all status displays"""
        self.update_config_status()
        self.update_service_status()
        self.check_backend_status()
        self.refresh_system_metrics()
        self.main_app.add_log("Status refreshed")

    def refresh_system_metrics(self):
        """Refresh system metrics from backend"""
        try:
            response = requests.get(f"{self.api_base_url}/api/system/status", timeout=3)
            if response.status_code == 200:
                status_data = response.json()
                self.update_system_metrics_display(status_data)
        except Exception as e:
            logger.error(f"Error refreshing system metrics: {e}")
            # Clear metrics if backend unavailable
            for item in self.metrics_tree.get_children():
                self.metrics_tree.delete(item)
            self.metrics_tree.insert(
                "",
                "end",
                values=("Backend Status", "Unavailable - Cannot fetch metrics"),
            )

    def test_backend_api(self):
        """Test backend API endpoints"""
        self.main_app.add_log("Testing backend API endpoints...")

        endpoints = [
            ("/", "Root"),
            ("/health", "Health Check"),
            ("/api/system/status", "System Status"),
            ("/api/chat/characters", "Chat Characters"),
        ]

        for endpoint, name in endpoints:
            try:
                response = requests.get(f"{self.api_base_url}{endpoint}", timeout=2)
                status = (
                    "✓ OK"
                    if response.status_code == 200
                    else f"✗ {response.status_code}"
                )
                self.main_app.add_log(f"{name}: {status}")
            except Exception as e:
                self.main_app.add_log(f"{name}: ✗ Error - {e}")

    def view_logs(self):
        """Switch to logs tab"""
        if self.main_app and hasattr(self.main_app, "notebook"):
            # Switch to logs tab (index 3)
            self.main_app.notebook.select(3)

    def update_system_metrics_display(self, status_data: Dict[str, Any]):
        """Update system metrics display"""
        # Clear existing items
        for item in self.metrics_tree.get_children():
            self.metrics_tree.delete(item)

        # Add status items
        self.metrics_tree.insert(
            "", "end", values=("Backend Status", status_data.get("status", "unknown"))
        )
        self.metrics_tree.insert(
            "", "end", values=("Uptime", f"{status_data.get('uptime', 0):.2f} seconds")
        )
        self.metrics_tree.insert(
            "", "end", values=("CPU Usage", f"{status_data.get('cpu_usage', 0):.1f}%")
        )
        self.metrics_tree.insert(
            "",
            "end",
            values=("Memory Usage", f"{status_data.get('memory_usage', 0):.1f}%"),
        )

        disk_usage = status_data.get("disk_usage", {})
        if isinstance(disk_usage, dict):
            self.metrics_tree.insert(
                "", "end", values=("Disk Usage", f"{disk_usage.get('percent', 0):.1f}%")
            )

        # Services status
        services = status_data.get("services", {})
        for service, status in services.items():
            self.metrics_tree.insert("", "end", values=(f"Service: {service}", status))

        # Request/response metrics if available
        if "requests_total" in status_data:
            self.metrics_tree.insert(
                "", "end", values=("Total Requests", status_data["requests_total"])
            )
        if "active_connections" in status_data:
            self.metrics_tree.insert(
                "",
                "end",
                values=("Active Connections", status_data["active_connections"]),
            )

    def update_connection_status(self):
        """Update connection status display"""
        # This is called from the main app - update service status
        self.update_service_status()

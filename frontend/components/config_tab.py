"""
Configuration tab component
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from typing import Optional, Any
import logging
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from .base_component import BaseComponent

logger = logging.getLogger(__name__)


class ConfigTab(BaseComponent):
    """Configuration tab"""
    
    def __init__(self, parent: tk.Widget, main_app: Optional[Any] = None):
        super().__init__(parent, main_app)
        
    def create(self):
        """Create configuration tab UI"""
        self.frame = ttk.Frame(self.parent)
        
        # API Configuration
        api_frame = ttk.LabelFrame(self.frame, text="API Configuration")
        api_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.api_host_var = tk.StringVar(value=self.main_app.settings.api_host)
        self.api_port_var = tk.StringVar(value=str(self.main_app.settings.api_port))
        
        ttk.Label(api_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(api_frame, textvariable=self.api_host_var).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        
        ttk.Label(api_frame, text="Port:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(api_frame, textvariable=self.api_port_var).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        
        api_frame.columnconfigure(1, weight=1)
        
        # Audio Configuration
        audio_frame = ttk.LabelFrame(self.frame, text="Audio Configuration")
        audio_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.sample_rate_var = tk.StringVar(value=str(self.main_app.settings.sample_rate))
        self.channels_var = tk.StringVar(value=str(self.main_app.settings.channels))
        
        ttk.Label(audio_frame, text="Sample Rate:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(audio_frame, textvariable=self.sample_rate_var).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        
        ttk.Label(audio_frame, text="Channels:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(audio_frame, textvariable=self.channels_var).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        
        audio_frame.columnconfigure(1, weight=1)
        
        # Model Configuration
        model_frame = ttk.LabelFrame(self.frame, text="Model Configuration")
        model_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.whisper_model_var = tk.StringVar(value=self.main_app.settings.whisper_model)
        self.piper_model_var = tk.StringVar(value=str(self.main_app.settings.piper_model_path))
        
        ttk.Label(model_frame, text="Whisper Model:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(model_frame, textvariable=self.whisper_model_var).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        
        ttk.Label(model_frame, text="Piper Model:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(model_frame, textvariable=self.piper_model_var).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        
        model_frame.columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        save_button = ttk.Button(button_frame, text="Save Configuration", command=self.save_config)
        save_button.pack(side=tk.LEFT, padx=(0, 5))
        
        reload_button = ttk.Button(button_frame, text="Reload Configuration", command=self.reload_config)
        reload_button.pack(side=tk.LEFT)
        
        # Store widgets
        self.add_widget("api_host_var", self.api_host_var)
        self.add_widget("api_port_var", self.api_port_var)
        self.add_widget("sample_rate_var", self.sample_rate_var)
        self.add_widget("channels_var", self.channels_var)
        self.add_widget("whisper_model_var", self.whisper_model_var)
        self.add_widget("piper_model_var", self.piper_model_var)
        
        # Webhooks management UI
        webhooks_frame = ttk.LabelFrame(self.frame, text="Webhooks")
        webhooks_frame.pack(fill=tk.BOTH, padx=5, pady=5)
        
        self.webhook_listbox = tk.Listbox(webhooks_frame, height=5)
        self.webhook_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=5)
        
        webhook_scroll = ttk.Scrollbar(webhooks_frame, orient=tk.VERTICAL, command=self.webhook_listbox.yview)
        self.webhook_listbox.configure(yscrollcommand=webhook_scroll.set)
        webhook_scroll.pack(side=tk.LEFT, fill=tk.Y, padx=(0,5), pady=5)
        
        webhook_buttons = ttk.Frame(webhooks_frame)
        webhook_buttons.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        add_hook_btn = ttk.Button(webhook_buttons, text="Add", command=self.add_webhook)
        add_hook_btn.pack(fill=tk.X, pady=(0,5))
        remove_hook_btn = ttk.Button(webhook_buttons, text="Remove", command=self.remove_webhook)
        remove_hook_btn.pack(fill=tk.X, pady=(0,5))
        test_hook_btn = ttk.Button(webhook_buttons, text="Test", command=self.test_webhook)
        test_hook_btn.pack(fill=tk.X)
        
        # Register webhook widgets for access
        self.add_widget("webhook_listbox", self.webhook_listbox)
        self.add_widget("add_hook_btn", add_hook_btn)
        self.add_widget("remove_hook_btn", remove_hook_btn)
        self.add_widget("test_hook_btn", test_hook_btn)
    
    def save_config(self):
        """Save configuration"""
        try:
            # Update settings
            self.main_app.settings.api_host = self.api_host_var.get()
            self.main_app.settings.api_port = int(self.api_port_var.get())
            self.main_app.settings.sample_rate = int(self.sample_rate_var.get())
            self.main_app.settings.channels = int(self.channels_var.get())
            self.main_app.settings.whisper_model = self.whisper_model_var.get()
            self.main_app.settings.piper_model_path = Path(self.piper_model_var.get())
            
            # Save to .env file
            env_content = f"""# VTuber Backend Configuration
# Updated by GUI

# API Configuration
API_HOST={self.main_app.settings.api_host}
API_PORT={self.main_app.settings.api_port}

# Audio Settings
SAMPLE_RATE={self.main_app.settings.sample_rate}
CHANNELS={self.main_app.settings.channels}

# Model Settings
WHISPER_MODEL={self.main_app.settings.whisper_model}
PIPER_MODEL_PATH={self.main_app.settings.piper_model_path}

# Character Settings
CHARACTER_NAME={self.main_app.settings.character_name}
CHARACTER_PROFILE={self.main_app.settings.character_profile}
CHARACTER_PERSONALITY={self.main_app.settings.character_personality}

# Logging
LOG_LEVEL={self.main_app.settings.log_level}
LOG_FILE={self.main_app.settings.log_file}
"""
            
            with open(".env", "w") as f:
                f.write(env_content)
            
            messagebox.showinfo("Success", "Configuration saved successfully")
            self.add_log("Configuration saved")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def reload_config(self):
        """Reload configuration"""
        try:
            from config import get_settings
            self.main_app.settings = get_settings()
            self.api_host_var.set(self.main_app.settings.api_host)
            self.api_port_var.set(str(self.main_app.settings.api_port))
            self.sample_rate_var.set(str(self.main_app.settings.sample_rate))
            self.channels_var.set(str(self.main_app.settings.channels))
            self.whisper_model_var.set(self.main_app.settings.whisper_model)
            self.piper_model_var.set(str(self.main_app.settings.piper_model_path))
            
            messagebox.showinfo("Success", "Configuration reloaded successfully")
            self.add_log("Configuration reloaded")
            
            # Refresh webhook list after reload
            try:
                self.refresh_webhooks()
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Error reloading configuration: {e}")
            messagebox.showerror("Error", f"Failed to reload configuration: {e}")
    
    # Webhook management methods
    def refresh_webhooks(self):
        """Fetch registered webhooks from backend and populate listbox"""
        try:
            response = requests.get(f"http://{self.main_app.settings.api_host}:{self.main_app.settings.api_port}/api/system/webhooks")
            if response.status_code == 200:
                hooks = response.json().get("webhooks", [])
                self.webhook_listbox.delete(0, tk.END)
                for h in hooks:
                    self.webhook_listbox.insert(tk.END, h)
            else:
                self.add_log(f"Failed to get webhooks: {response.status_code}")
        except Exception as e:
            logger.error(f"Error refreshing webhooks: {e}")
            self.add_log(f"Error refreshing webhooks: {e}")
    
    def add_webhook(self):
        """Prompt for a webhook URL and register it with backend"""
        try:
            url = simpledialog.askstring("Add Webhook", "Webhook URL (https://...):")
            if not url:
                return
            response = requests.post(
                f"http://{self.main_app.settings.api_host}:{self.main_app.settings.api_port}/api/webhooks",
                json={"url": url}
            )
            if response.status_code == 200:
                self.add_log(f"Webhook registered: {url}")
                self.refresh_webhooks()
            else:
                self.add_log(f"Failed to register webhook: {response.status_code}")
        except Exception as e:
            logger.error(f"Error adding webhook: {e}")
            self.add_log(f"Error adding webhook: {e}")
    
    def remove_webhook(self):
        """Remove the selected webhook"""
        try:
            sel = self.webhook_listbox.curselection()
            if not sel:
                messagebox.showwarning("Remove Webhook", "Select a webhook to remove")
                return
            url = self.webhook_listbox.get(sel[0])
            response = requests.delete(
                f"http://{self.main_app.settings.api_host}:{self.main_app.settings.api_port}/api/webhooks",
                params={"url": url}
            )
            if response.status_code == 200:
                self.add_log(f"Webhook removed: {url}")
                self.refresh_webhooks()
            else:
                self.add_log(f"Failed to remove webhook: {response.status_code}")
        except Exception as e:
            logger.error(f"Error removing webhook: {e}")
            self.add_log(f"Error removing webhook: {e}")
    
    def test_webhook(self):
        """Trigger a test event to validate webhook delivery"""
        try:
            # Ask for optional message
            msg = simpledialog.askstring("Test Webhooks", "Test message (optional):", initialvalue="webhook test")
            response = requests.post(
                f"http://{self.main_app.settings.api_host}:{self.main_app.settings.api_port}/api/webhooks/test",
                json=msg if isinstance(msg, str) else {"message": "webhook test"}
            )
            if response.status_code == 200:
                self.add_log("Webhook test event emitted")
            else:
                self.add_log(f"Webhook test failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Error testing webhook: {e}")
            self.add_log(f"Error testing webhook: {e}")
    
    def add_log(self, message: str):
        """Add log message"""
        if hasattr(self.main_app, 'add_log'):
            self.main_app.add_log(message)
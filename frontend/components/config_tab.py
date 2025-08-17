"""
Configuration tab component
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional
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
            
        except Exception as e:
            logger.error(f"Error reloading configuration: {e}")
            messagebox.showerror("Error", f"Failed to reload configuration: {e}")
    
    def add_log(self, message: str):
        """Add log message"""
        if hasattr(self.main_app, 'add_log'):
            self.main_app.add_log(message)
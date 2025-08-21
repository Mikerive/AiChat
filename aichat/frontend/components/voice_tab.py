"""
Voice training tab component
"""

import logging
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any, Dict, Optional

import requests

from .base_component import BaseComponent

logger = logging.getLogger(__name__)


class VoiceTab(BaseComponent):
    """Voice training tab"""

    def __init__(self, parent: tk.Widget, main_app: Optional[Any] = None):
        super().__init__(parent, main_app)
        self.api_base_url = (
            f"http://{main_app.settings.api_host}:{main_app.settings.api_port}"
        )

    def create(self):
        """Create voice training tab UI"""
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Upload frame
        upload_frame = ttk.LabelFrame(self.frame, text="Upload Audio")
        upload_frame.pack(fill=tk.X, padx=5, pady=5)

        self.upload_button = ttk.Button(
            upload_frame, text="Upload Audio File", command=self.upload_audio
        )
        self.upload_button.pack(pady=5)

        # Training frame
        training_frame = ttk.LabelFrame(self.frame, text="Voice Training")
        training_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Training controls
        controls_frame = ttk.Frame(training_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(controls_frame, text="Model Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.model_name_var = tk.StringVar(value="custom_voice")
        self.model_name_entry = ttk.Entry(
            controls_frame, textvariable=self.model_name_var
        )
        self.model_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Label(controls_frame, text="Epochs:").pack(side=tk.LEFT, padx=(10, 5))
        self.epochs_var = tk.StringVar(value="10")
        self.epochs_entry = ttk.Entry(
            controls_frame, textvariable=self.epochs_var, width=10
        )
        self.epochs_entry.pack(side=tk.LEFT, padx=(0, 5))

        self.train_button = ttk.Button(
            controls_frame, text="Start Training", command=self.start_training
        )
        self.train_button.pack(side=tk.LEFT, padx=5)

        # Progress display
        self.progress_text = scrolledtext.ScrolledText(
            training_frame, wrap=tk.WORD, height=10
        )
        self.progress_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Models frame
        models_frame = ttk.LabelFrame(self.frame, text="Voice Models")
        models_frame.pack(fill=tk.X, padx=5, pady=5)

        self.models_tree = ttk.Treeview(
            models_frame,
            columns=("Name", "Status", "Created"),
            show="headings",
            height=5,
        )
        self.models_tree.heading("Name", text="Name")
        self.models_tree.heading("Status", text="Status")
        self.models_tree.heading("Created", text="Created")
        self.models_tree.column("Name", width=150)
        self.models_tree.column("Status", width=100)
        self.models_tree.column("Created", width=150)

        models_scrollbar = ttk.Scrollbar(
            models_frame, orient=tk.VERTICAL, command=self.models_tree.yview
        )
        self.models_tree.configure(yscrollcommand=models_scrollbar.set)

        self.models_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        models_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        refresh_models_button = ttk.Button(
            models_frame, text="Refresh Models", command=self.refresh_models
        )
        refresh_models_button.pack(pady=5)

        # Store widgets
        self.add_widget("model_name_var", self.model_name_var)
        self.add_widget("model_name_entry", self.model_name_entry)
        self.add_widget("epochs_var", self.epochs_var)
        self.add_widget("epochs_entry", self.epochs_entry)
        self.add_widget("train_button", self.train_button)
        self.add_widget("progress_text", self.progress_text)
        self.add_widget("models_tree", self.models_tree)

    def upload_audio(self):
        """Upload audio file"""
        file_path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio Files", "*.wav *.mp3 *.m4a *.ogg"),
                ("All Files", "*.*"),
            ],
        )

        if file_path:
            try:
                with open(file_path, "rb") as f:
                    files = {"file": f}
                    response = requests.post(
                        f"{self.api_base_url}/api/voice/upload", files=files
                    )

                if response.status_code == 200:
                    result = response.json()
                    self.add_log(f"Audio uploaded: {result.get('filename', '')}")
                else:
                    self.add_log(f"Upload error: {response.status_code}")
            except Exception as e:
                logger.error(f"Error uploading audio: {e}")
                self.add_log(f"Upload error: {e}")

    def start_training(self):
        """Start voice training"""
        model_name = self.model_name_var.get().strip()
        epochs = int(self.epochs_var.get().strip())

        if not model_name:
            messagebox.showerror("Error", "Please enter a model name")
            return

        try:
            response = requests.post(
                f"{self.api_base_url}/api/voice/train",
                json={"model_name": model_name, "epochs": epochs, "batch_size": 8},
            )

            if response.status_code == 200:
                result = response.json()
                self.add_log(f"Training started: {result.get('model_name', '')}")
                self.progress_text.delete(1.0, tk.END)
                self.progress_text.insert(
                    tk.END, f"Training started for {model_name}\n"
                )
            else:
                self.add_log(f"Training error: {response.status_code}")
        except Exception as e:
            logger.error(f"Error starting training: {e}")
            self.add_log(f"Training error: {e}")

    def add_training_progress(self, progress_data: Dict[str, Any]):
        """Add training progress to display"""
        epoch = progress_data.get("epoch", 0)
        total_epochs = progress_data.get("total_epochs", 1)
        loss = progress_data.get("loss", 0)

        progress_text = f"Epoch {epoch}/{total_epochs}, Loss: {loss:.4f}\n"
        self.progress_text.insert(tk.END, progress_text)
        self.progress_text.see(tk.END)

    def refresh_models(self):
        """Refresh voice models"""
        try:
            response = requests.get(f"{self.api_base_url}/api/voice/models")
            if response.status_code == 200:
                models = response.json().get("models", [])

                # Clear existing items
                for item in self.models_tree.get_children():
                    self.models_tree.delete(item)

                # Add models
                for model in models:
                    self.models_tree.insert(
                        "",
                        "end",
                        values=(
                            model.get("name", ""),
                            model.get("status", ""),
                            (
                                model.get("created_at", "")[:19]
                                if model.get("created_at")
                                else ""
                            ),
                        ),
                    )
        except Exception as e:
            logger.error(f"Error refreshing models: {e}")

    def refresh(self):
        """Refresh component data"""
        self.refresh_models()

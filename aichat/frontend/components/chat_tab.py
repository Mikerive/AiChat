"""
Chat interface tab component
"""

import logging
import tkinter as tk
from datetime import datetime
from tkinter import scrolledtext, ttk
from typing import Any, Optional

import requests

# Third-party imports
import tkinter as tk
from tkinter import scrolledtext, ttk

# Local imports
from .base_component import BaseComponent

logger = logging.getLogger(__name__)


class ChatTab(BaseComponent):
    """Chat interface tab"""

    def __init__(self, parent: tk.Widget, main_app: Optional[Any] = None):
        super().__init__(parent, main_app)
        self.api_base_url = (
            f"http://{main_app.settings.api_host}:{main_app.settings.api_port}"
        )

    def create(self):
        """Create chat tab UI"""
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Character selection
        char_frame = ttk.LabelFrame(self.frame, text="Character")
        char_frame.pack(fill=tk.X, padx=5, pady=5)

        self.character_var = tk.StringVar(value="hatsune_miku")
        self.character_combo = ttk.Combobox(
            char_frame, textvariable=self.character_var, state="readonly"
        )
        self.character_combo.pack(side=tk.LEFT, padx=5, pady=5)
        self.character_combo.bind("<<ComboboxSelected>>", self.on_character_selected)

        # Chat interface
        chat_display_frame = ttk.LabelFrame(self.frame, text="Chat")
        chat_display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Chat display
        self.chat_text = scrolledtext.ScrolledText(
            chat_display_frame, wrap=tk.WORD, height=15
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Input frame
        input_frame = ttk.Frame(chat_display_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.chat_entry = ttk.Entry(input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_entry.bind("<Return>", self.send_chat_message)

        send_button = ttk.Button(
            input_frame, text="Send", command=self.send_chat_message
        )
        send_button.pack(side=tk.RIGHT)

        # TTS frame
        tts_frame = ttk.LabelFrame(self.frame, text="Text-to-Speech")
        tts_frame.pack(fill=tk.X, padx=5, pady=5)

        self.tts_text = ttk.Entry(tts_frame)
        self.tts_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        tts_button = ttk.Button(
            tts_frame, text="Generate TTS", command=self.generate_tts
        )
        tts_button.pack(side=tk.RIGHT)

        # Audio playback frame
        audio_frame = ttk.LabelFrame(self.frame, text="Audio Playback")
        audio_frame.pack(fill=tk.X, padx=5, pady=5)

        self.audio_path_label = ttk.Label(audio_frame, text="No audio file selected")
        self.audio_path_label.pack(side=tk.LEFT, padx=5)

        self.play_button = ttk.Button(
            audio_frame, text="Play", command=self.play_audio, state=tk.DISABLED
        )
        self.play_button.pack(side=tk.RIGHT, padx=5)

        # Store widgets
        self.add_widget("character_var", self.character_var)
        self.add_widget("character_combo", self.character_combo)
        self.add_widget("chat_text", self.chat_text)
        self.add_widget("chat_entry", self.chat_entry)
        self.add_widget("tts_text", self.tts_text)
        self.add_widget("audio_path_label", self.audio_path_label)
        self.add_widget("play_button", self.play_button)

    def refresh_characters(self):
        """Refresh character list"""
        try:
            response = requests.get(f"{self.api_base_url}/api/chat/characters")
            if response.status_code == 200:
                data = response.json()
                # Handle both dict and list responses
                if isinstance(data, dict):
                    characters = data.get("characters", [])
                elif isinstance(data, list):
                    characters = data
                else:
                    characters = []

                # Handle both string and dict character entries
                character_names = []
                for char in characters:
                    if isinstance(char, dict):
                        character_names.append(char.get("name", str(char)))
                    else:
                        character_names.append(str(char))

                self.character_combo["values"] = character_names
                if character_names and not self.character_var.get():
                    self.character_var.set(character_names[0])
        except Exception as e:
            logger.error(f"Error refreshing characters: {e}")

    def send_chat_message(self, event=None):
        """Send chat message"""
        message = self.chat_entry.get().strip()
        if not message:
            return

        character = self.character_var.get()

        try:
            response = requests.post(
                f"{self.api_base_url}/api/chat",
                json={"text": message, "character": character},
            )

            if response.status_code == 200:
                result = response.json()
                self.add_chat_message("You", message)
                self.add_chat_message("Character", result.get("response", ""))
                self.chat_entry.delete(0, tk.END)
            else:
                self.add_log(f"Chat error: {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending chat message: {e}")
            self.add_log(f"Chat error: {e}")

    def add_chat_message(self, sender: str, message: str):
        """Add chat message to display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        chat_line = f"[{timestamp}] {sender}: {message}\n"
        self.chat_text.insert(tk.END, chat_line)
        self.chat_text.see(tk.END)

    def generate_tts(self):
        """Generate text-to-speech"""
        text = self.tts_text.get().strip()
        if not text:
            return

        character = self.character_var.get()

        try:
            response = requests.post(
                f"{self.api_base_url}/api/tts",
                json={"text": text, "character": character},
            )

            if response.status_code == 200:
                result = response.json()
                audio_path = result.get("audio_path", "")
                self.audio_path_label.config(text=audio_path)
                self.play_button.config(state=tk.NORMAL)
                self.add_log(f"TTS generated: {audio_path}")
            else:
                self.add_log(f"TTS error: {response.status_code}")
        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            self.add_log(f"TTS error: {e}")

    def play_audio(self):
        """Play audio file"""
        # This would use a proper audio library in a real implementation
        self.add_log("Audio playback not implemented yet")

    def on_character_selected(self, event):
        """Handle character selection"""
        character = self.character_var.get()
        self.add_log(f"Character selected: {character}")

    def refresh(self):
        """Refresh component data"""
        self.refresh_characters()

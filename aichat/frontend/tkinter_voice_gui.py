#!/usr/bin/env python3
"""
Interactive Voice VTuber GUI using Tkinter
Real-time voice interaction with push-to-talk and always-listening modes
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional
import subprocess
import sys

# Audio imports (with fallbacks)
try:
    import pyaudio
    import numpy as np
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False
    
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Local imports
try:
    from aichat.backend.services.chat.service_manager import get_whisper_service, get_chat_service
    from aichat.constants.paths import ensure_dirs, TEMP_AUDIO_DIR
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False

logger = logging.getLogger(__name__)

class VoiceVTuberGUI:
    """Interactive Voice VTuber GUI with real-time audio processing"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎤 VTuber Voice Interface")
        self.root.geometry("800x700")
        self.root.configure(bg='#2b2b2b')
        
        # Audio setup
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.is_listening = False  # Always listening mode
        self.push_to_talk = False  # Push to talk mode
        
        # Backend connection
        self.backend_url = "http://localhost:8765"
        self.backend_process = None
        
        # Services (will be initialized if available)
        self.whisper_service = None
        self.chat_service = None
        
        # Setup GUI
        self.setup_gui()
        self.setup_audio()
        self.setup_backend_services()
        
        # Start audio processing thread
        self.audio_thread = threading.Thread(target=self.audio_processing_loop, daemon=True)
        self.audio_thread.start()
        
        # Start backend check thread
        self.backend_thread = threading.Thread(target=self.backend_monitor_loop, daemon=True)
        self.backend_thread.start()
        
    def setup_gui(self):
        """Setup the GUI layout"""
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="🎤 VTuber Voice Interface", 
                              font=("Arial", 16, "bold"), bg='#2b2b2b', fg='white')
        title_label.pack(pady=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="System Status", padding="5")
        status_frame.pack(fill=tk.X, pady=5)
        
        self.backend_status = tk.Label(status_frame, text="Backend: Checking...", 
                                      font=("Arial", 10), bg='#2b2b2b', fg='yellow')
        self.backend_status.pack(anchor=tk.W)
        
        self.audio_status = tk.Label(status_frame, text=f"Audio: {'Available' if HAS_AUDIO else 'Not Available'}", 
                                    font=("Arial", 10), bg='#2b2b2b', 
                                    fg='green' if HAS_AUDIO else 'red')
        self.audio_status.pack(anchor=tk.W)
        
        # Voice controls frame
        controls_frame = ttk.LabelFrame(main_frame, text="Voice Controls", padding="5")
        controls_frame.pack(fill=tk.X, pady=5)
        
        # Voice mode selection
        mode_frame = ttk.Frame(controls_frame)
        mode_frame.pack(fill=tk.X, pady=2)
        
        self.voice_mode = tk.StringVar(value="push")
        tk.Radiobutton(mode_frame, text="Push to Talk", variable=self.voice_mode, value="push",
                      command=self.change_voice_mode, bg='#2b2b2b', fg='white', selectcolor='#2b2b2b').pack(side=tk.LEFT)
        tk.Radiobutton(mode_frame, text="Always Listening", variable=self.voice_mode, value="always",
                      command=self.change_voice_mode, bg='#2b2b2b', fg='white', selectcolor='#2b2b2b').pack(side=tk.LEFT)
        
        # Voice buttons
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.talk_button = tk.Button(button_frame, text="🎤 Hold to Talk", 
                                    font=("Arial", 12, "bold"), bg='#4CAF50', fg='white',
                                    relief=tk.RAISED, bd=3)
        self.talk_button.pack(side=tk.LEFT, padx=5)
        self.talk_button.bind("<ButtonPress-1>", self.start_recording)
        self.talk_button.bind("<ButtonRelease-1>", self.stop_recording)
        
        self.listen_button = tk.Button(button_frame, text="🔊 Start Listening", 
                                      font=("Arial", 12, "bold"), bg='#2196F3', fg='white',
                                      command=self.toggle_listening, relief=tk.RAISED, bd=3)
        self.listen_button.pack(side=tk.LEFT, padx=5)
        
        # Volume indicator
        self.volume_var = tk.DoubleVar()
        self.volume_bar = ttk.Progressbar(button_frame, variable=self.volume_var, 
                                         maximum=100, length=150)
        self.volume_bar.pack(side=tk.LEFT, padx=10, pady=5)
        tk.Label(button_frame, text="Volume", bg='#2b2b2b', fg='white').pack(side=tk.LEFT)
        
        # Chat area
        chat_frame = ttk.LabelFrame(main_frame, text="Conversation", padding="5")
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.chat_display = scrolledtext.ScrolledText(chat_frame, height=15, width=70,
                                                     bg='#1e1e1e', fg='white', font=("Arial", 10),
                                                     insertbackground='white')
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        self.text_input = tk.Entry(input_frame, font=("Arial", 12), bg='#1e1e1e', fg='white',
                                  insertbackground='white')
        self.text_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.text_input.bind("<Return>", self.send_text_message)
        
        self.send_button = tk.Button(input_frame, text="Send", font=("Arial", 12),
                                    bg='#4CAF50', fg='white', command=self.send_text_message)
        self.send_button.pack(side=tk.RIGHT)
        
        # Backend controls
        backend_frame = ttk.LabelFrame(main_frame, text="Backend Controls", padding="5")
        backend_frame.pack(fill=tk.X, pady=5)
        
        self.start_backend_btn = tk.Button(backend_frame, text="🚀 Start Backend", 
                                          font=("Arial", 10), bg='#FF9800', fg='white',
                                          command=self.start_backend)
        self.start_backend_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_backend_btn = tk.Button(backend_frame, text="⏹️ Stop Backend", 
                                         font=("Arial", 10), bg='#F44336', fg='white',
                                         command=self.stop_backend)
        self.stop_backend_btn.pack(side=tk.LEFT, padx=5)
        
        # Add initial message
        self.add_chat_message("System", "VTuber Voice Interface initialized! 🎤", "system")
        
    def setup_audio(self):
        """Initialize audio components"""
        if not HAS_AUDIO:
            self.add_chat_message("System", "⚠️ PyAudio not available. Voice features disabled.", "warning")
            return
            
        try:
            self.audio = pyaudio.PyAudio()
            self.sample_rate = 16000
            self.chunk_size = 1024
            self.channels = 1
            self.format = pyaudio.paInt16
            
            # Get default input device
            try:
                self.input_device = self.audio.get_default_input_device_info()
                device_name = self.input_device['name']
                self.add_chat_message("System", f"🎤 Audio device: {device_name}", "info")
            except Exception as e:
                self.add_chat_message("System", f"⚠️ No audio input device found: {e}", "warning")
                
        except Exception as e:
            self.add_chat_message("System", f"❌ Audio setup failed: {e}", "error")
            
    def setup_backend_services(self):
        """Initialize backend services if available"""
        if not HAS_BACKEND:
            self.add_chat_message("System", "⚠️ Backend services not available. Using API mode.", "warning")
            return
            
        try:
            # Initialize services directly
            self.whisper_service = get_whisper_service()
            self.chat_service = get_chat_service()
            self.add_chat_message("System", "✅ Backend services initialized", "success")
        except Exception as e:
            self.add_chat_message("System", f"⚠️ Backend services failed: {e}", "warning")
            
    def change_voice_mode(self):
        """Handle voice mode changes"""
        mode = self.voice_mode.get()
        if mode == "push":
            self.push_to_talk = True
            self.is_listening = False
            self.talk_button.configure(state=tk.NORMAL)
            self.listen_button.configure(text="🔊 Start Listening", bg='#2196F3')
            self.add_chat_message("System", "Mode: Push to Talk", "info")
        else:
            self.push_to_talk = False
            self.talk_button.configure(state=tk.DISABLED)
            self.add_chat_message("System", "Mode: Always Listening", "info")
            
    def start_recording(self, event=None):
        """Start recording audio"""
        if not HAS_AUDIO or not self.push_to_talk:
            return
            
        self.is_recording = True
        self.talk_button.configure(text="🔴 Recording...", bg='#F44336')
        self.add_chat_message("System", "🎤 Recording started...", "info")
        
    def stop_recording(self, event=None):
        """Stop recording and process audio"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.talk_button.configure(text="🎤 Hold to Talk", bg='#4CAF50')
        self.add_chat_message("System", "⏹️ Recording stopped, processing...", "info")
        
        # Process the recorded audio
        threading.Thread(target=self.process_recorded_audio, daemon=True).start()
        
    def toggle_listening(self):
        """Toggle always listening mode"""
        if not HAS_AUDIO:
            messagebox.showwarning("Audio Error", "Audio not available")
            return
            
        self.is_listening = not self.is_listening
        
        if self.is_listening:
            self.listen_button.configure(text="🔇 Stop Listening", bg='#F44336')
            self.add_chat_message("System", "👂 Always listening mode activated", "success")
        else:
            self.listen_button.configure(text="🔊 Start Listening", bg='#2196F3')
            self.add_chat_message("System", "⏸️ Always listening mode deactivated", "info")
            
    def process_recorded_audio(self):
        """Process recorded audio and generate response"""
        try:
            # Simulate audio processing
            time.sleep(1)  # Simulate processing time
            
            # For now, use placeholder text
            user_text = "Hello, this is a test voice message"
            self.add_chat_message("You", user_text, "user")
            
            # Generate AI response
            self.generate_ai_response(user_text)
            
        except Exception as e:
            self.add_chat_message("System", f"❌ Audio processing failed: {e}", "error")
            
    def generate_ai_response(self, user_input: str):
        """Generate AI response to user input"""
        try:
            # Placeholder response generation
            ai_responses = [
                f"I heard you say: '{user_input}'. That's interesting!",
                f"Thanks for sharing that! You mentioned: '{user_input}'",
                f"I understand you said: '{user_input}'. Can you tell me more?",
                f"That's a great point about '{user_input}'. Let me think about that..."
            ]
            
            import random
            response = random.choice(ai_responses)
            
            self.add_chat_message("AI", response, "ai")
            
            # Simulate TTS generation
            self.add_chat_message("System", "🔊 Playing AI response...", "info")
            
        except Exception as e:
            self.add_chat_message("System", f"❌ AI response failed: {e}", "error")
            
    def send_text_message(self, event=None):
        """Send text message"""
        text = self.text_input.get().strip()
        if not text:
            return
            
        self.text_input.delete(0, tk.END)
        self.add_chat_message("You", text, "user")
        
        # Generate AI response
        threading.Thread(target=lambda: self.generate_ai_response(text), daemon=True).start()
        
    def add_chat_message(self, sender: str, message: str, msg_type: str = "normal"):
        """Add message to chat display"""
        def update_chat():
            timestamp = time.strftime("%H:%M:%S")
            
            # Color coding
            colors = {
                "user": "#4CAF50",
                "ai": "#2196F3", 
                "system": "#FF9800",
                "info": "#00BCD4",
                "success": "#4CAF50",
                "warning": "#FF9800",
                "error": "#F44336"
            }
            
            color = colors.get(msg_type, "#FFFFFF")
            
            self.chat_display.configure(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_display.insert(tk.END, f"{sender}: ", f"sender_{msg_type}")
            self.chat_display.insert(tk.END, f"{message}\\n", f"message_{msg_type}")
            
            # Configure tags (fix tag names)
            tag_name = f"{msg_type}_{timestamp}"  # Unique tag names
            self.chat_display.tag_configure("timestamp", foreground="#888888", font=("Arial", 8))
            self.chat_display.tag_configure(f"sender_{msg_type}", foreground=color, font=("Arial", 10, "bold"))
            self.chat_display.tag_configure(f"message_{msg_type}", foreground="#FFFFFF", font=("Arial", 10))
            
            self.chat_display.configure(state=tk.DISABLED)
            self.chat_display.see(tk.END)
            
        # Ensure GUI updates happen on main thread
        self.root.after(0, update_chat)
        
    def audio_processing_loop(self):
        """Main audio processing loop"""
        while True:
            try:
                if self.is_listening and HAS_AUDIO:
                    # Simulate real-time volume monitoring
                    volume = np.random.randint(0, 100)
                    self.root.after(0, lambda v=volume: self.volume_var.set(v))
                    
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Audio processing error: {e}")
                time.sleep(1)
                
    def backend_monitor_loop(self):
        """Monitor backend status"""
        while True:
            try:
                if HAS_REQUESTS:
                    try:
                        response = requests.get(f"{self.backend_url}/api/system/status", timeout=2)
                        if response.status_code == 200:
                            self.root.after(0, lambda: self.backend_status.configure(
                                text="Backend: ✅ Connected", fg="green"))
                        else:
                            self.root.after(0, lambda: self.backend_status.configure(
                                text="Backend: ⚠️ Error", fg="orange"))
                    except:
                        self.root.after(0, lambda: self.backend_status.configure(
                            text="Backend: ❌ Not Connected", fg="red"))
                else:
                    self.root.after(0, lambda: self.backend_status.configure(
                        text="Backend: ❓ Unknown (requests not available)", fg="yellow"))
                        
            except Exception as e:
                logger.error(f"Backend monitor error: {e}")
                
            time.sleep(5)  # Check every 5 seconds
            
    def start_backend(self):
        """Start backend process"""
        try:
            if self.backend_process and self.backend_process.poll() is None:
                messagebox.showinfo("Backend", "Backend already running")
                return
                
            self.add_chat_message("System", "🚀 Starting backend...", "info")
            
            self.backend_process = subprocess.Popen([
                sys.executable, "-m", "aichat.cli.main", 
                "backend", "--host", "localhost", "--port", "8765"
            ], cwd=Path.cwd())
            
            self.add_chat_message("System", f"Backend started (PID: {self.backend_process.pid})", "success")
            
        except Exception as e:
            self.add_chat_message("System", f"❌ Backend start failed: {e}", "error")
            
    def stop_backend(self):
        """Stop backend process"""
        try:
            if self.backend_process and self.backend_process.poll() is None:
                self.backend_process.terminate()
                self.add_chat_message("System", "⏹️ Backend stopped", "info")
            else:
                self.add_chat_message("System", "No backend process to stop", "warning")
                
        except Exception as e:
            self.add_chat_message("System", f"❌ Backend stop failed: {e}", "error")
            
    def on_closing(self):
        """Handle window closing"""
        if self.backend_process and self.backend_process.poll() is None:
            self.backend_process.terminate()
            
        if HAS_AUDIO and hasattr(self, 'audio'):
            self.audio.terminate()
            
        self.root.destroy()
        
    def run(self):
        """Run the GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        app = VoiceVTuberGUI()
        app.run()
    except KeyboardInterrupt:
        print("\\nApplication interrupted")
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
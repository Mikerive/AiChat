"""
Chat Display Panel - Shows conversation history
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Dict, Any, List, Tuple
import time
import json
import logging
from datetime import datetime

from .base import PanelComponent
from ..theme import theme
from ..models import ChatMessage, MessageType, ChatDisplayConfig

logger = logging.getLogger(__name__)


class ChatDisplayPanel(PanelComponent):
    """Panel for displaying chat conversation"""
    
    def __init__(self, parent: tk.Widget, app_controller=None):
        self.chat_history: List[ChatMessage] = []
        self.max_messages = 1000
        self.display_config = ChatDisplayConfig()
        super().__init__(parent, "Conversation", app_controller)
        
    def _setup_component(self):
        """Setup chat display"""
        # Chat display area
        display_frame = ttk.Frame(self.frame)
        display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create scrolled text widget
        self.widgets['chat_display'] = scrolledtext.ScrolledText(
            display_frame,
            height=20, width=80,
            bg=theme.colors.bg_primary, fg=theme.colors.text_primary,
            font=theme.fonts.body,
            insertbackground=theme.colors.text_primary,
            selectbackground=theme.colors.accent_primary,
            selectforeground=theme.colors.text_white,
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief='solid',
            borderwidth=2,
            highlightcolor=theme.colors.accent_primary,
            highlightthickness=1
        )
        self.widgets['chat_display'].pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for different message types
        self._configure_text_tags()
        
        # Input area
        input_frame = ttk.Frame(self.frame)
        input_frame.pack(fill=tk.X)
        
        # Text input
        self.widgets['text_input'] = tk.Entry(
            input_frame, 
            font=theme.fonts.body,
            bg=theme.colors.bg_primary, fg=theme.colors.text_primary,
            insertbackground=theme.colors.text_primary,
            relief='solid', bd=2,
            highlightcolor=theme.colors.accent_primary,
            highlightthickness=1
        )
        self.widgets['text_input'].pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.widgets['text_input'].bind('<Return>', self._send_text_message)
        self.widgets['text_input'].bind('<KeyPress>', self._on_typing)
        
        # Send button
        self.widgets['send_button'] = self.create_button(
            input_frame, "Send", command=self._send_text_message,
            style='Accent.TButton')
        self.widgets['send_button'].pack(side=tk.RIGHT)
        
        # Control buttons
        control_frame = ttk.Frame(self.frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.widgets['clear_button'] = self.create_button(
            control_frame, "🗑️ Clear Chat", command=self.clear_chat)
        self.widgets['clear_button'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['export_button'] = self.create_button(
            control_frame, "💾 Export Chat", command=self.export_chat)
        self.widgets['export_button'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['auto_scroll_var'] = tk.BooleanVar(value=True)
        self.widgets['auto_scroll_check'] = ttk.Checkbutton(
            control_frame, text="Auto-scroll",
            variable=self.widgets['auto_scroll_var'])
        self.widgets['auto_scroll_check'].pack(side=tk.RIGHT)
        
        # Add initial welcome message
        self.add_message("System", "VTuber Voice Interface Ready! 🎤", "system")
        
    def _configure_text_tags(self):
        """Configure text tags for different message types with alignment"""
        chat_display = self.widgets['chat_display']
        
        # Timestamp tag - centered
        chat_display.tag_configure("timestamp", 
                                  foreground=theme.colors.text_muted, 
                                  font=theme.fonts.caption,
                                  justify='center')
        
        # User message tags - left aligned  
        chat_display.tag_configure("user_sender", 
                                  foreground=theme.colors.success, 
                                  font=theme.fonts.subheading,
                                  justify='left')
        chat_display.tag_configure("user_message", 
                                  foreground=theme.colors.text_primary, 
                                  font=theme.fonts.body,
                                  justify='left',
                                  lmargin1=self.display_config.user_indent_left,
                                  lmargin2=self.display_config.user_indent_left,
                                  rmargin=self.display_config.user_indent_right,
                                  wrap='word')
        
        # Voice message tags - left aligned (similar to user)
        chat_display.tag_configure("voice_sender", 
                                  foreground=theme.colors.success, 
                                  font=theme.fonts.subheading,
                                  justify='left')
        chat_display.tag_configure("voice_message", 
                                  foreground=theme.colors.text_primary, 
                                  font=theme.fonts.body,
                                  justify='left',
                                  lmargin1=self.display_config.user_indent_left,
                                  lmargin2=self.display_config.user_indent_left,
                                  rmargin=self.display_config.user_indent_right,
                                  wrap='word')
        
        # AI message tags - right aligned
        chat_display.tag_configure("ai_sender", 
                                  foreground=theme.colors.accent_primary, 
                                  font=theme.fonts.subheading,
                                  justify='right')
        chat_display.tag_configure("ai_message", 
                                  foreground=theme.colors.text_primary, 
                                  font=theme.fonts.body,
                                  justify='right',
                                  lmargin1=self.display_config.ai_indent_left,
                                  lmargin2=self.display_config.ai_indent_left,
                                  rmargin=self.display_config.ai_indent_right,
                                  wrap='word')
        
        # System message tags - center aligned
        chat_display.tag_configure("system_sender", 
                                  foreground=theme.colors.warning, 
                                  font=theme.fonts.subheading,
                                  justify='center')
        chat_display.tag_configure("system_message", 
                                  foreground=theme.colors.text_secondary, 
                                  font=theme.fonts.body,
                                  justify='center',
                                  lmargin1=self.display_config.center_indent,
                                  lmargin2=self.display_config.center_indent,
                                  rmargin=self.display_config.center_indent,
                                  wrap='word')
        
        # Status message tags - center aligned
        for status_type in ['info', 'success', 'warning', 'error']:
            color = getattr(theme.colors, status_type, theme.colors.info)
            chat_display.tag_configure(f"{status_type}_sender", 
                                      foreground=color, 
                                      font=theme.fonts.subheading,
                                      justify='center')
            chat_display.tag_configure(f"{status_type}_message", 
                                      foreground=theme.colors.text_secondary, 
                                      font=theme.fonts.body,
                                      justify='center',
                                      lmargin1=self.display_config.center_indent,
                                      lmargin2=self.display_config.center_indent,
                                      rmargin=self.display_config.center_indent,
                                      wrap='word')
                                  
    def add_message(self, sender: str, message: str, msg_type: str = "user", 
                   metadata: Dict[str, Any] = None):
        """Add a message to the chat display (legacy method)"""
        # Convert to new message type enum
        try:
            message_type = MessageType(msg_type)
        except ValueError:
            message_type = MessageType.SYSTEM
            
        # Create ChatMessage object
        chat_message = ChatMessage(
            sender=sender,
            content=message,
            message_type=message_type,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.add_chat_message(chat_message)
    
    def add_chat_message(self, chat_message: ChatMessage):
        """Add a ChatMessage object to the display"""
        # Store in history
        self.chat_history.append(chat_message)
        
        # Limit history size
        if len(self.chat_history) > self.max_messages:
            self.chat_history = self.chat_history[-self.max_messages:]
            
        # Add to display
        self._add_message_to_display(chat_message)
        
        # Emit event for other components
        self.emit_event('message_added', chat_message.to_dict())
        
    def _add_message_to_display(self, chat_message: ChatMessage):
        """Add ChatMessage to the display widget with proper formatting"""
        chat_display = self.widgets['chat_display']
        chat_display.configure(state=tk.NORMAL)
        
        # Add some spacing between messages
        if len(self.chat_history) > 1:
            chat_display.insert(tk.END, "\n", "system_message")
        
        # Format message display based on alignment
        if chat_message.is_center_aligned:
            # Center aligned messages (system, status)
            chat_display.insert(tk.END, f"[{chat_message.timestamp_str}] ", "timestamp")
            chat_display.insert(tk.END, f"{chat_message.display_sender}: ", chat_message.sender_tag)
            chat_display.insert(tk.END, f"{chat_message.content}\n", chat_message.message_tag)
            
        elif chat_message.is_left_aligned:
            # Left aligned messages (user, voice)
            chat_display.insert(tk.END, f"[{chat_message.timestamp_str}] ", "timestamp")
            chat_display.insert(tk.END, f"\n{chat_message.display_sender}:\n", chat_message.sender_tag)
            chat_display.insert(tk.END, f"{chat_message.content}\n", chat_message.message_tag)
            
        else:  # right aligned (AI)
            # Right aligned messages (AI)
            chat_display.insert(tk.END, f"[{chat_message.timestamp_str}] ", "timestamp")
            chat_display.insert(tk.END, f"\n{chat_message.display_sender}:\n", chat_message.sender_tag)
            chat_display.insert(tk.END, f"{chat_message.content}\n", chat_message.message_tag)
        
        chat_display.configure(state=tk.DISABLED)
        
        # Auto-scroll if enabled
        if self.widgets['auto_scroll_var'].get():
            chat_display.see(tk.END)
            
    def _send_text_message(self, event=None):
        """Send text message"""
        text = self.widgets['text_input'].get().strip()
        if not text:
            return "break"  # Prevent default Enter behavior
            
        # Clear input
        self.widgets['text_input'].delete(0, tk.END)
        
        # Add user message
        self.add_message("You", text, "user")
        
        # Emit event for processing
        self.emit_event('text_message_sent', text)
        
        return "break"  # Prevent default Enter behavior
        
    def _on_typing(self, event):
        """Handle typing events"""
        # Emit typing event (could be used for "user is typing" indicators)
        self.emit_event('user_typing')
        
    def add_ai_response(self, response: str, metadata: Dict[str, Any] = None):
        """Add AI response to chat"""
        emotion = metadata.get('emotion') if metadata else None
        model_used = metadata.get('model_used') if metadata else None
        
        chat_message = ChatMessage.create_ai_message(
            content=response,
            sender="AI",
            emotion=emotion,
            model_used=model_used
        )
        chat_message.metadata = metadata or {}
        self.add_chat_message(chat_message)
        
    def add_system_message(self, message: str, msg_type: str = "system"):
        """Add system message"""
        try:
            message_type = MessageType(msg_type)
        except ValueError:
            message_type = MessageType.SYSTEM
            
        chat_message = ChatMessage.create_system_message(
            content=message,
            msg_type=message_type,
            sender="System"
        )
        self.add_chat_message(chat_message)
        
    def add_voice_message(self, transcription: str, confidence: float = None):
        """Add voice transcription message"""
        chat_message = ChatMessage.create_voice_message(
            content=transcription,
            confidence=confidence,
            sender="You"
        )
        self.add_chat_message(chat_message)
        
    def add_user_message(self, message: str, sender: str = "You"):
        """Add user message"""
        chat_message = ChatMessage.create_user_message(
            content=message,
            sender=sender
        )
        self.add_chat_message(chat_message)
        
    def clear_chat(self):
        """Clear chat display and history"""
        self.chat_history.clear()
        chat_display = self.widgets['chat_display']
        chat_display.configure(state=tk.NORMAL)
        chat_display.delete(1.0, tk.END)
        chat_display.configure(state=tk.DISABLED)
        
        # Add confirmation message
        self.add_system_message("Chat cleared", "info")
        self.emit_event('chat_cleared')
        
    def export_chat(self):
        """Export chat to file"""
        if not self.chat_history:
            self.show_info("No chat history to export")
            return
            
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[
                    ("JSON files", "*.json"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ],
                title="Export Chat History"
            )
            
            if filename:
                if filename.endswith('.json'):
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(self.chat_history, f, indent=2, ensure_ascii=False)
                else:
                    # Export as plain text
                    with open(filename, 'w', encoding='utf-8') as f:
                        for entry in self.chat_history:
                            f.write(f"[{entry['timestamp']}] {entry['sender']}: {entry['message']}\n")
                            
                self.show_success(f"Chat exported to {filename}")
                
        except Exception as e:
            self.show_error(f"Export failed: {e}")
            
    def search_messages(self, query: str) -> List[Dict[str, Any]]:
        """Search messages containing query"""
        query_lower = query.lower()
        results = []
        
        for entry in self.chat_history:
            if (query_lower in entry['message'].lower() or 
                query_lower in entry['sender'].lower()):
                results.append(entry)
                
        return results
        
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages"""
        return self.chat_history[-count:] if self.chat_history else []
        
    def update_state(self, state: Dict[str, Any]):
        """Update chat display state"""
        if 'auto_scroll' in state:
            self.widgets['auto_scroll_var'].set(state['auto_scroll'])
            
        if 'max_messages' in state:
            self.max_messages = state['max_messages']
            
    def get_state(self) -> Dict[str, Any]:
        """Get current chat display state"""
        return {
            'message_count': len(self.chat_history),
            'auto_scroll': self.widgets['auto_scroll_var'].get(),
            'max_messages': self.max_messages
        }
"""
Character Manager Panel - Character switching, profiles, and management
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, List, Optional
import logging
import threading
import json
from datetime import datetime

from .base import PanelComponent
from ..theme import theme
from ..models import CharacterProfile

logger = logging.getLogger(__name__)


class CharacterManagerPanel(PanelComponent):
    """Panel for managing AI characters and switching between them"""
    
    def __init__(self, parent: tk.Widget, app_controller=None):
        self.characters: List[CharacterProfile] = []
        self.current_character: Optional[CharacterProfile] = None
        self.character_cache = {}
        self.voice_preview_playing = False
        super().__init__(parent, "Character Manager", app_controller)
        
    def _setup_component(self):
        """Setup character manager interface"""
        # Character list frame
        list_frame = ttk.Frame(self.frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Character list with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable character list
        self.widgets['char_listbox'] = tk.Listbox(
            list_container,
            font=theme.fonts.body,
            bg=theme.colors.bg_primary,
            fg=theme.colors.text_primary,
            selectbackground=theme.colors.accent_primary,
            selectforeground=theme.colors.text_white,
            relief='solid',
            bd=1,
            highlightcolor=theme.colors.accent_primary,
            highlightthickness=1
        )
        
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.widgets['char_listbox'].configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.widgets['char_listbox'].yview)
        
        self.widgets['char_listbox'].pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.widgets['char_listbox'].bind('<<ListboxSelect>>', self._on_character_select)
        self.widgets['char_listbox'].bind('<Double-Button-1>', self._on_character_activate)
        
        # Character info frame
        info_frame = ttk.LabelFrame(self.frame, text="Character Details", style='Modern.TLabelframe')
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Character details grid
        details_frame = ttk.Frame(info_frame)
        details_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Name
        self.create_label(details_frame, "Name:", style='Heading.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.widgets['char_name'] = self.create_label(
            details_frame, "No character selected", style='Normal.TLabel')
        self.widgets['char_name'].grid(row=0, column=1, sticky=tk.W)
        
        # Description
        self.create_label(details_frame, "Description:", style='Heading.TLabel').grid(
            row=1, column=0, sticky=tk.NW, padx=(0, 10), pady=(5, 0))
        self.widgets['char_desc'] = self.create_label(
            details_frame, "Select a character to view details", 
            style='Normal.TLabel', wraplength=200)
        self.widgets['char_desc'].grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # Voice Model
        self.create_label(details_frame, "Voice Model:", style='Heading.TLabel').grid(
            row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.widgets['char_voice'] = self.create_label(
            details_frame, "Not specified", style='Normal.TLabel')
        self.widgets['char_voice'].grid(row=2, column=1, sticky=tk.W, pady=(5, 0))
        
        # Status indicator
        self.create_label(details_frame, "Status:", style='Heading.TLabel').grid(
            row=3, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.widgets['char_status'] = self.create_label(
            details_frame, "●", style='Normal.TLabel')
        self.widgets['char_status'].grid(row=3, column=1, sticky=tk.W, pady=(5, 0))
        
        # Voice preview frame
        preview_frame = ttk.LabelFrame(self.frame, text="Voice Preview", style='Modern.TLabelframe')
        preview_frame.pack(fill=tk.X, pady=(0, 10))
        
        preview_controls = ttk.Frame(preview_frame)
        preview_controls.pack(fill=tk.X, padx=10, pady=10)
        
        # Sample text entry
        self.create_label(preview_controls, "Sample Text:", style='Heading.TLabel').pack(anchor=tk.W)
        self.widgets['sample_text'] = tk.Entry(
            preview_controls,
            font=theme.fonts.body,
            bg=theme.colors.bg_primary,
            fg=theme.colors.text_primary,
            insertbackground=theme.colors.text_primary,
            relief='solid', bd=1,
            highlightcolor=theme.colors.accent_primary,
            highlightthickness=1
        )
        self.widgets['sample_text'].pack(fill=tk.X, pady=(5, 10))
        self.widgets['sample_text'].insert(0, "Hello! This is a voice preview.")
        
        # Preview controls
        preview_btn_frame = ttk.Frame(preview_controls)
        preview_btn_frame.pack(fill=tk.X)
        
        self.widgets['play_preview_btn'] = self.create_button(
            preview_btn_frame, "▶️ Play Preview", 
            command=self._play_voice_preview, style='Accent.TButton')
        self.widgets['play_preview_btn'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['stop_preview_btn'] = self.create_button(
            preview_btn_frame, "⏹️ Stop", 
            command=self._stop_voice_preview)
        self.widgets['stop_preview_btn'].pack(side=tk.LEFT, padx=(0, 5))
        self.widgets['stop_preview_btn'].configure(state='disabled')
        
        # Management buttons
        mgmt_frame = ttk.Frame(self.frame)
        mgmt_frame.pack(fill=tk.X)
        
        self.widgets['activate_btn'] = self.create_button(
            mgmt_frame, "🎯 Activate Character", 
            command=self._activate_character, style='Success.TButton')
        self.widgets['activate_btn'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['new_char_btn'] = self.create_button(
            mgmt_frame, "➕ New Character", 
            command=self._create_new_character)
        self.widgets['new_char_btn'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['edit_char_btn'] = self.create_button(
            mgmt_frame, "✏️ Edit", 
            command=self._edit_character)
        self.widgets['edit_char_btn'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['delete_char_btn'] = self.create_button(
            mgmt_frame, "🗑️ Delete", 
            command=self._delete_character, style='Danger.TButton')
        self.widgets['delete_char_btn'].pack(side=tk.LEFT, padx=(0, 5))
        
        self.widgets['refresh_btn'] = self.create_button(
            mgmt_frame, "🔄 Refresh", 
            command=self.refresh_characters)
        self.widgets['refresh_btn'].pack(side=tk.RIGHT)
        
        # Initially disable character-specific buttons
        self._update_button_states()
        
        # Load initial characters
        self.refresh_characters()
        
    def _on_character_select(self, event=None):
        """Handle character selection"""
        selection = self.widgets['char_listbox'].curselection()
        if not selection:
            self._clear_character_details()
            return
            
        try:
            index = selection[0]
            if 0 <= index < len(self.characters):
                character = self.characters[index]
                self._display_character_details(character)
                self._update_button_states(True)
        except Exception as e:
            logger.error(f"Error selecting character: {e}")
            
    def _on_character_activate(self, event=None):
        """Handle double-click to activate character"""
        self._activate_character()
        
    def _display_character_details(self, character: CharacterProfile):
        """Display character details in the info panel"""
        self.widgets['char_name'].configure(text=character.name)
        self.widgets['char_desc'].configure(text=character.description or "No description")
        self.widgets['char_voice'].configure(text=character.voice_model or "Default")
        
        # Status indicator
        if character.is_active:
            status_text = "🟢 Active"
            status_color = theme.colors.success
        else:
            status_text = "⚪ Inactive"
            status_color = theme.colors.text_muted
            
        self.widgets['char_status'].configure(text=status_text, foreground=status_color)
        
    def _clear_character_details(self):
        """Clear character details display"""
        self.widgets['char_name'].configure(text="No character selected")
        self.widgets['char_desc'].configure(text="Select a character to view details")
        self.widgets['char_voice'].configure(text="Not specified")
        self.widgets['char_status'].configure(text="●", foreground=theme.colors.text_muted)
        self._update_button_states(False)
        
    def _update_button_states(self, character_selected=False):
        """Update button states based on selection"""
        state = 'normal' if character_selected else 'disabled'
        self.widgets['activate_btn'].configure(state=state)
        self.widgets['edit_char_btn'].configure(state=state)
        self.widgets['delete_char_btn'].configure(state=state)
        self.widgets['play_preview_btn'].configure(state=state)
        
    def _get_selected_character(self) -> Optional[CharacterProfile]:
        """Get currently selected character"""
        selection = self.widgets['char_listbox'].curselection()
        if not selection:
            return None
            
        try:
            index = selection[0]
            return self.characters[index] if 0 <= index < len(self.characters) else None
        except Exception:
            return None
            
    def _activate_character(self):
        """Activate the selected character"""
        character = self._get_selected_character()
        if not character:
            self.show_warning("Please select a character to activate")
            return
            
        try:
            # Call backend to switch character
            if hasattr(self.app_controller, 'backend_client'):
                def switch_character():
                    try:
                        result = self.app_controller.backend_client.switch_character(character.name)
                        
                        def on_success():
                            # Update local state
                            for char in self.characters:
                                char.is_active = (char.id == character.id)
                                
                            self._refresh_character_list()
                            self._display_character_details(character)
                            self.current_character = character
                            
                            # Emit event
                            self.emit_event('character_activated', {
                                'character': character.to_dict(),
                                'response': result
                            })
                            
                            self.show_success(f"Activated character: {character.name}")
                            
                        def on_error(error_msg):
                            self.show_error(f"Failed to activate character: {error_msg}")
                            
                        if result.get('status') == 'success':
                            self.frame.after(0, on_success)
                        else:
                            self.frame.after(0, lambda: on_error(result.get('message', 'Unknown error')))
                            
                    except Exception as e:
                        error_msg = str(e)
                        self.frame.after(0, lambda: on_error(error_msg))
                        
                # Run in background thread
                threading.Thread(target=switch_character, daemon=True).start()
                self.widgets['activate_btn'].configure(text="Switching...", state='disabled')
                self.frame.after(3000, lambda: self.widgets['activate_btn'].configure(
                    text="🎯 Activate Character", state='normal'))
                    
            else:
                self.show_error("Backend client not available")
                
        except Exception as e:
            logger.error(f"Error activating character: {e}")
            self.show_error(f"Failed to activate character: {e}")
            
    def _play_voice_preview(self):
        """Play voice preview for selected character"""
        character = self._get_selected_character()
        if not character:
            return
            
        sample_text = self.widgets['sample_text'].get().strip()
        if not sample_text:
            self.show_warning("Please enter sample text for preview")
            return
            
        try:
            if hasattr(self.app_controller, 'backend_client'):
                def generate_preview():
                    try:
                        result = self.app_controller.backend_client.generate_tts(
                            text=sample_text,
                            character_id=character.name
                        )
                        
                        def on_success():
                            self.voice_preview_playing = True
                            self.widgets['play_preview_btn'].configure(state='disabled')
                            self.widgets['stop_preview_btn'].configure(state='normal')
                            
                            # Auto re-enable after reasonable time
                            self.frame.after(5000, self._stop_voice_preview)
                            
                        def on_error(error_msg):
                            self.show_error(f"Preview failed: {error_msg}")
                            
                        if result.get('status') == 'success':
                            self.frame.after(0, on_success)
                        else:
                            self.frame.after(0, lambda: on_error(result.get('message', 'Unknown error')))
                            
                    except Exception as e:
                        error_msg = str(e)
                        self.frame.after(0, lambda: on_error(error_msg))
                        
                threading.Thread(target=generate_preview, daemon=True).start()
                self.widgets['play_preview_btn'].configure(text="Generating...", state='disabled')
                
        except Exception as e:
            logger.error(f"Error playing preview: {e}")
            self.show_error(f"Preview failed: {e}")
            
    def _stop_voice_preview(self):
        """Stop voice preview"""
        self.voice_preview_playing = False
        self.widgets['play_preview_btn'].configure(text="▶️ Play Preview", state='normal')
        self.widgets['stop_preview_btn'].configure(state='disabled')
        
    def _create_new_character(self):
        """Create new character"""
        self._open_character_editor()
        
    def _edit_character(self):
        """Edit selected character"""
        character = self._get_selected_character()
        if character:
            self._open_character_editor(character)
        else:
            self.show_warning("Please select a character to edit")
            
    def _delete_character(self):
        """Delete selected character"""
        character = self._get_selected_character()
        if not character:
            self.show_warning("Please select a character to delete")
            return
            
        # Confirm deletion
        if not messagebox.askyesno(
            "Delete Character",
            f"Are you sure you want to delete '{character.name}'?\n\nThis action cannot be undone."
        ):
            return
            
        try:
            # TODO: Call backend to delete character
            # For now, just remove from local list
            self.characters.remove(character)
            self._refresh_character_list()
            self._clear_character_details()
            self.show_success(f"Deleted character: {character.name}")
            
        except Exception as e:
            logger.error(f"Error deleting character: {e}")
            self.show_error(f"Failed to delete character: {e}")
            
    def _open_character_editor(self, character: Optional[CharacterProfile] = None):
        """Open character editor dialog"""
        editor = CharacterEditorDialog(self.frame, character)
        if editor.result:
            # Character was saved, refresh list
            self.refresh_characters()
            
    def refresh_characters(self):
        """Refresh character list from backend"""
        try:
            if hasattr(self.app_controller, 'backend_client'):
                def fetch_characters():
                    try:
                        result = self.app_controller.backend_client.get_characters()
                        
                        def on_success():
                            if 'characters' in result:
                                # Convert to CharacterProfile objects
                                self.characters = [
                                    CharacterProfile.from_dict(char_data)
                                    for char_data in result['characters']
                                ]
                            else:
                                self.characters = []
                                
                            self._refresh_character_list()
                            self.show_info(f"Loaded {len(self.characters)} characters")
                            
                        def on_error(error_msg):
                            self.show_error(f"Failed to load characters: {error_msg}")
                            # Use fallback characters
                            self._load_fallback_characters()
                            
                        if result.get('status') != 'error':
                            self.frame.after(0, on_success)
                        else:
                            self.frame.after(0, lambda: on_error(result.get('message', 'Unknown error')))
                            
                    except Exception as e:
                        error_msg = str(e)
                        self.frame.after(0, lambda: on_error(error_msg))
                        
                threading.Thread(target=fetch_characters, daemon=True).start()
            else:
                self._load_fallback_characters()
                
        except Exception as e:
            logger.error(f"Error refreshing characters: {e}")
            self._load_fallback_characters()
            
    def _load_fallback_characters(self):
        """Load fallback characters for demo purposes"""
        self.characters = [
            CharacterProfile(
                id="hatsune_miku",
                name="Hatsune Miku", 
                description="Virtual singer with turquoise hair. Cheerful and energetic personality.",
                voice_model="miku_v2",
                is_active=True
            ),
            CharacterProfile(
                id="assistant",
                name="AI Assistant",
                description="General purpose AI assistant. Helpful and professional.",
                voice_model="default",
                is_active=False
            )
        ]
        self._refresh_character_list()
        
    def _refresh_character_list(self):
        """Refresh the character listbox display"""
        # Clear current list
        self.widgets['char_listbox'].delete(0, tk.END)
        
        # Add characters
        for character in self.characters:
            display_name = character.name
            if character.is_active:
                display_name = f"● {display_name} (Active)"
            else:
                display_name = f"○ {display_name}"
                
            self.widgets['char_listbox'].insert(tk.END, display_name)
            
        # Select active character if any
        for i, character in enumerate(self.characters):
            if character.is_active:
                self.widgets['char_listbox'].selection_set(i)
                self._display_character_details(character)
                break
                
    def update_state(self, state: Dict[str, Any]):
        """Update character manager state"""
        if 'refresh_characters' in state and state['refresh_characters']:
            self.refresh_characters()
            
        if 'current_character' in state:
            char_name = state['current_character']
            # Find and activate character
            for character in self.characters:
                if character.name == char_name:
                    character.is_active = True
                    self.current_character = character
                else:
                    character.is_active = False
            self._refresh_character_list()
            
    def get_state(self) -> Dict[str, Any]:
        """Get current character manager state"""
        return {
            'character_count': len(self.characters),
            'current_character': self.current_character.name if self.current_character else None,
            'characters': [char.to_dict() for char in self.characters]
        }


class CharacterEditorDialog:
    """Dialog for creating/editing characters"""
    
    def __init__(self, parent, character: Optional[CharacterProfile] = None):
        self.character = character
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self._setup_dialog()
        
    def _setup_dialog(self):
        """Setup character editor dialog"""
        self.dialog.title("Character Editor" if not self.character else f"Edit {self.character.name}")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient()
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"500x400+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Form fields
        # Name
        ttk.Label(main_frame, text="Name:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        self.name_var = tk.StringVar(value=self.character.name if self.character else "")
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, font=('Segoe UI', 10))
        name_entry.pack(fill=tk.X, pady=(5, 15))
        
        # Description
        ttk.Label(main_frame, text="Description:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        desc_frame = ttk.Frame(main_frame)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        
        self.desc_text = tk.Text(
            desc_frame, height=6, font=('Segoe UI', 9),
            relief='solid', bd=1, wrap=tk.WORD
        )
        desc_scroll = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=self.desc_text.yview)
        self.desc_text.configure(yscrollcommand=desc_scroll.set)
        
        self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        if self.character and self.character.description:
            self.desc_text.insert('1.0', self.character.description)
            
        # Voice Model
        ttk.Label(main_frame, text="Voice Model:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        self.voice_var = tk.StringVar(value=self.character.voice_model if self.character else "default")
        voice_combo = ttk.Combobox(main_frame, textvariable=self.voice_var, 
                                 values=["default", "miku_v2", "assistant", "custom"])
        voice_combo.pack(fill=tk.X, pady=(5, 15))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        save_btn = ttk.Button(button_frame, text="💾 Save", command=self._save_character)
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        cancel_btn = ttk.Button(button_frame, text="❌ Cancel", command=self._cancel)
        cancel_btn.pack(side=tk.RIGHT)
        
        # Focus name field
        name_entry.focus_set()
        
        # Wait for dialog to close
        self.dialog.wait_window()
        
    def _save_character(self):
        """Save character changes"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Validation Error", "Character name is required")
            return
            
        description = self.desc_text.get('1.0', tk.END).strip()
        voice_model = self.voice_var.get().strip()
        
        if self.character:
            # Edit existing character
            self.character.name = name
            self.character.description = description
            self.character.voice_model = voice_model
            self.result = self.character
        else:
            # Create new character
            self.result = CharacterProfile(
                id=name.lower().replace(' ', '_'),
                name=name,
                description=description,
                voice_model=voice_model
            )
            
        self.dialog.destroy()
        
    def _cancel(self):
        """Cancel editing"""
        self.result = None
        self.dialog.destroy()
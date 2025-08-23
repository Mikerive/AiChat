"""
Centralized theme and styling system for VTuber GUI
"""

import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ColorPalette:
    """Complete color palette for the application"""
    # Base colors
    white: str = '#ffffff'
    black: str = '#000000'
    
    # Background colors
    bg_primary: str = '#ffffff'      # Main background
    bg_secondary: str = '#f8f9fa'    # Secondary panels
    bg_tertiary: str = '#e9ecef'     # Input backgrounds
    bg_hover: str = '#f5f5f5'        # Hover states
    
    # Text colors
    text_primary: str = '#212529'    # Main text
    text_secondary: str = '#6c757d'  # Subtitle text
    text_muted: str = '#adb5bd'      # Placeholder text
    text_white: str = '#ffffff'      # White text for dark backgrounds
    
    # Accent colors - Professional blue theme
    accent_primary: str = '#0d6efd'      # Primary actions
    accent_primary_hover: str = '#0b5ed7' # Primary hover
    accent_secondary: str = '#6f42c1'     # Secondary actions
    
    # Status colors
    success: str = '#198754'         # Success states
    success_hover: str = '#157347'   # Success hover
    warning: str = '#fd7e14'         # Warning states
    warning_hover: str = '#e8670e'   # Warning hover
    danger: str = '#dc3545'          # Error/danger states
    danger_hover: str = '#bb2d3b'    # Danger hover
    info: str = '#0dcaf0'            # Info states
    info_hover: str = '#3dd5f3'      # Info hover
    
    # Border colors
    border_light: str = '#dee2e6'    # Light borders
    border_medium: str = '#ced4da'   # Medium borders
    border_dark: str = '#6c757d'     # Strong borders
    
    # Special colors for voice interface
    voice_recording: str = '#dc3545'  # Recording indicator
    voice_listening: str = '#198754'  # Listening indicator
    voice_processing: str = '#fd7e14' # Processing indicator


@dataclass 
class FontSet:
    """Complete font definitions"""
    # Font families
    primary_family: str = 'Segoe UI'
    mono_family: str = 'Consolas'
    
    # Font sizes and styles
    title: tuple = ('Segoe UI', 18, 'bold')        # Main titles
    heading: tuple = ('Segoe UI', 14, 'bold')      # Section headings
    subheading: tuple = ('Segoe UI', 12, 'bold')   # Subsection headings
    body: tuple = ('Segoe UI', 10, 'normal')       # Body text
    body_bold: tuple = ('Segoe UI', 10, 'bold')    # Bold body text
    caption: tuple = ('Segoe UI', 9, 'normal')     # Small text
    button: tuple = ('Segoe UI', 10, 'bold')       # Button text
    mono: tuple = ('Consolas', 9, 'normal')        # Monospace text


@dataclass
class Spacing:
    """Spacing and sizing constants"""
    # Padding values
    xs: int = 2
    sm: int = 4
    md: int = 8
    lg: int = 12
    xl: int = 16
    xxl: int = 24
    
    # Component sizes
    button_height: int = 36
    input_height: int = 32
    tab_height: int = 40
    
    # Layout dimensions
    sidebar_width: int = 300
    panel_min_width: int = 250
    window_min_width: int = 900
    window_min_height: int = 600


class VTuberTheme:
    """Main theme class that combines all styling"""
    
    def __init__(self):
        self.colors = ColorPalette()
        self.fonts = FontSet()
        self.spacing = Spacing()
        self.style = None
        
    def setup_ttk_styles(self, root: tk.Tk):
        """Configure all TTK styles"""
        self.style = ttk.Style()
        self.style.theme_use('default')
        
        # Configure basic styles
        self._configure_frames()
        self._configure_labels()
        self._configure_buttons()
        self._configure_entries()
        self._configure_notebook()
        self._configure_treeview()
        self._configure_progressbar()
        self._configure_scale()
        self._configure_checkbutton()
        self._configure_radiobutton()
        self._configure_combobox()
        self._configure_scrollbar()
        
    def _configure_frames(self):
        """Configure frame styles"""
        # Main frames
        self.style.configure('Main.TFrame',
                           background=self.colors.bg_primary,
                           relief='flat',
                           borderwidth=0)
                           
        self.style.configure('Panel.TFrame',
                           background=self.colors.bg_secondary,
                           relief='solid',
                           borderwidth=1,
                           bordercolor=self.colors.border_light)
                           
        self.style.configure('Card.TFrame',
                           background=self.colors.bg_primary,
                           relief='solid',
                           borderwidth=1,
                           bordercolor=self.colors.border_light)
                           
    def _configure_labels(self):
        """Configure label styles"""
        base_config = {'background': self.colors.bg_primary}
        
        self.style.configure('Title.TLabel',
                           **base_config,
                           foreground=self.colors.text_primary,
                           font=self.fonts.title)
                           
        self.style.configure('Heading.TLabel',
                           **base_config,
                           foreground=self.colors.text_primary,
                           font=self.fonts.heading)
                           
        self.style.configure('Subheading.TLabel',
                           **base_config,
                           foreground=self.colors.text_primary,
                           font=self.fonts.subheading)
                           
        self.style.configure('Body.TLabel',
                           **base_config,
                           foreground=self.colors.text_primary,
                           font=self.fonts.body)
                           
        self.style.configure('Caption.TLabel',
                           **base_config,
                           foreground=self.colors.text_secondary,
                           font=self.fonts.caption)
                           
        self.style.configure('Success.TLabel',
                           **base_config,
                           foreground=self.colors.success,
                           font=self.fonts.body_bold)
                           
        self.style.configure('Warning.TLabel',
                           **base_config,
                           foreground=self.colors.warning,
                           font=self.fonts.body_bold)
                           
        self.style.configure('Danger.TLabel',
                           **base_config,
                           foreground=self.colors.danger,
                           font=self.fonts.body_bold)
                           
    def _configure_buttons(self):
        """Configure button styles"""
        # Primary button
        self.style.configure('Primary.TButton',
                           background=self.colors.accent_primary,
                           foreground=self.colors.text_white,
                           font=self.fonts.button,
                           focuscolor='none',
                           borderwidth=0,
                           relief='flat',
                           padding=(self.spacing.md, self.spacing.sm))
        self.style.map('Primary.TButton',
                      background=[('active', self.colors.accent_primary_hover),
                                ('pressed', self.colors.accent_primary_hover)])
                      
        # Success button
        self.style.configure('Success.TButton',
                           background=self.colors.success,
                           foreground=self.colors.text_white,
                           font=self.fonts.button,
                           focuscolor='none',
                           borderwidth=0,
                           relief='flat',
                           padding=(self.spacing.md, self.spacing.sm))
        self.style.map('Success.TButton',
                      background=[('active', self.colors.success_hover),
                                ('pressed', self.colors.success_hover)])
                                
        # Warning button
        self.style.configure('Warning.TButton',
                           background=self.colors.warning,
                           foreground=self.colors.text_white,
                           font=self.fonts.button,
                           focuscolor='none',
                           borderwidth=0,
                           relief='flat',
                           padding=(self.spacing.md, self.spacing.sm))
        self.style.map('Warning.TButton',
                      background=[('active', self.colors.warning_hover),
                                ('pressed', self.colors.warning_hover)])
                                
        # Danger button
        self.style.configure('Danger.TButton',
                           background=self.colors.danger,
                           foreground=self.colors.text_white,
                           font=self.fonts.button,
                           focuscolor='none',
                           borderwidth=0,
                           relief='flat',
                           padding=(self.spacing.md, self.spacing.sm))
        self.style.map('Danger.TButton',
                      background=[('active', self.colors.danger_hover),
                                ('pressed', self.colors.danger_hover)])
                                
        # Secondary button (outline style)
        self.style.configure('Secondary.TButton',
                           background=self.colors.bg_primary,
                           foreground=self.colors.accent_primary,
                           font=self.fonts.button,
                           focuscolor='none',
                           borderwidth=2,
                           relief='solid',
                           bordercolor=self.colors.accent_primary,
                           padding=(self.spacing.md, self.spacing.sm))
        self.style.map('Secondary.TButton',
                      background=[('active', self.colors.bg_hover),
                                ('pressed', self.colors.bg_hover)])
                                
    def _configure_entries(self):
        """Configure entry widget styles"""
        self.style.configure('Modern.TEntry',
                           background=self.colors.bg_primary,
                           foreground=self.colors.text_primary,
                           font=self.fonts.body,
                           borderwidth=2,
                           relief='solid',
                           bordercolor=self.colors.border_medium,
                           focuscolor='none',
                           padding=(self.spacing.sm, self.spacing.xs))
        self.style.map('Modern.TEntry',
                      bordercolor=[('focus', self.colors.accent_primary)])
                      
    def _configure_notebook(self):
        """Configure notebook (tab) styles"""
        self.style.configure('Modern.TNotebook',
                           background=self.colors.bg_primary,
                           borderwidth=0,
                           tabmargins=[2, 5, 2, 0])
                           
        self.style.configure('Modern.TNotebook.Tab',
                           background=self.colors.bg_tertiary,
                           foreground=self.colors.text_primary,
                           font=self.fonts.body_bold,
                           padding=[self.spacing.lg, self.spacing.sm],
                           borderwidth=1,
                           relief='solid',
                           bordercolor=self.colors.border_light)
        self.style.map('Modern.TNotebook.Tab',
                      background=[('selected', self.colors.bg_primary),
                                ('active', self.colors.bg_hover)],
                      bordercolor=[('selected', self.colors.accent_primary)])
                      
    def _configure_treeview(self):
        """Configure treeview styles"""
        self.style.configure('Modern.Treeview',
                           background=self.colors.bg_primary,
                           foreground=self.colors.text_primary,
                           font=self.fonts.body,
                           borderwidth=1,
                           relief='solid',
                           bordercolor=self.colors.border_light)
        self.style.configure('Modern.Treeview.Heading',
                           background=self.colors.bg_secondary,
                           foreground=self.colors.text_primary,
                           font=self.fonts.body_bold,
                           borderwidth=1,
                           relief='solid')
                           
    def _configure_progressbar(self):
        """Configure progressbar styles"""
        self.style.configure('Modern.TProgressbar',
                           background=self.colors.accent_primary,
                           troughcolor=self.colors.bg_tertiary,
                           borderwidth=1,
                           relief='solid',
                           bordercolor=self.colors.border_light)
                           
    def _configure_scale(self):
        """Configure scale widget styles"""
        self.style.configure('Modern.TScale',
                           background=self.colors.bg_primary,
                           troughcolor=self.colors.bg_tertiary,
                           borderwidth=1,
                           relief='solid',
                           bordercolor=self.colors.border_light)
                           
    def _configure_checkbutton(self):
        """Configure checkbutton styles"""
        self.style.configure('Modern.TCheckbutton',
                           background=self.colors.bg_primary,
                           foreground=self.colors.text_primary,
                           font=self.fonts.body,
                           focuscolor='none')
                           
    def _configure_radiobutton(self):
        """Configure radiobutton styles"""
        self.style.configure('Modern.TRadiobutton',
                           background=self.colors.bg_primary,
                           foreground=self.colors.text_primary,
                           font=self.fonts.body,
                           focuscolor='none')
                           
    def _configure_combobox(self):
        """Configure combobox styles"""
        self.style.configure('Modern.TCombobox',
                           background=self.colors.bg_primary,
                           foreground=self.colors.text_primary,
                           font=self.fonts.body,
                           borderwidth=2,
                           relief='solid',
                           bordercolor=self.colors.border_medium)
        self.style.map('Modern.TCombobox',
                      bordercolor=[('focus', self.colors.accent_primary)])
                      
    def _configure_scrollbar(self):
        """Configure scrollbar styles"""
        self.style.configure('Modern.TScrollbar',
                           background=self.colors.bg_tertiary,
                           troughcolor=self.colors.bg_secondary,
                           borderwidth=0,
                           relief='flat')
                           
    def get_tk_colors(self) -> Dict[str, str]:
        """Get colors for traditional Tk widgets"""
        return {
            'bg': self.colors.bg_primary,
            'fg': self.colors.text_primary,
            'selectbackground': self.colors.accent_primary,
            'selectforeground': self.colors.text_white,
            'insertbackground': self.colors.text_primary,
            'highlightcolor': self.colors.accent_primary,
            'highlightbackground': self.colors.border_light,
            'activebackground': self.colors.bg_hover,
            'activeforeground': self.colors.text_primary
        }
        
    def get_menu_colors(self) -> Dict[str, str]:
        """Get colors for menu widgets"""
        return {
            'bg': self.colors.bg_primary,
            'fg': self.colors.text_primary,
            'activebackground': self.colors.accent_primary,
            'activeforeground': self.colors.text_white,
            'selectcolor': self.colors.accent_primary
        }


# Global theme instance
theme = VTuberTheme()


def apply_theme(root: tk.Tk):
    """Apply theme to the application"""
    theme.setup_ttk_styles(root)
    
    # Configure root window
    root.configure(bg=theme.colors.bg_primary)
    
    # Set default font
    root.option_add('*Font', theme.fonts.body)


# Utility functions for common styling patterns
def create_card_frame(parent, **kwargs) -> ttk.Frame:
    """Create a card-style frame"""
    return ttk.Frame(parent, style='Card.TFrame', **kwargs)


def create_panel_frame(parent, **kwargs) -> ttk.Frame:
    """Create a panel-style frame"""
    return ttk.Frame(parent, style='Panel.TFrame', **kwargs)


def create_primary_button(parent, text: str, command=None, **kwargs) -> ttk.Button:
    """Create a primary button"""
    return ttk.Button(parent, text=text, command=command, 
                     style='Primary.TButton', **kwargs)


def create_success_button(parent, text: str, command=None, **kwargs) -> ttk.Button:
    """Create a success button"""
    return ttk.Button(parent, text=text, command=command, 
                     style='Success.TButton', **kwargs)


def create_warning_button(parent, text: str, command=None, **kwargs) -> ttk.Button:
    """Create a warning button"""
    return ttk.Button(parent, text=text, command=command, 
                     style='Warning.TButton', **kwargs)


def create_danger_button(parent, text: str, command=None, **kwargs) -> ttk.Button:
    """Create a danger button"""
    return ttk.Button(parent, text=text, command=command, 
                     style='Danger.TButton', **kwargs)


def create_secondary_button(parent, text: str, command=None, **kwargs) -> ttk.Button:
    """Create a secondary button"""
    return ttk.Button(parent, text=text, command=command, 
                     style='Secondary.TButton', **kwargs)
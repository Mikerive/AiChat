"""
Utility functions and helpers for Tkinter GUI
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Callable, Any, Optional
import queue
import logging

logger = logging.getLogger(__name__)


# Colors and Fonts are now centralized in theme.py
# Import from theme if needed:
# from .theme import theme
# colors = theme.colors
# fonts = theme.fonts


def format_time_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"


class ThreadSafeQueue:
    """Thread-safe queue wrapper for GUI communication"""
    
    def __init__(self):
        self.queue = queue.Queue()
        
    def put(self, item):
        """Put item in queue"""
        self.queue.put(item)
        
    def get_all(self):
        """Get all items from queue"""
        items = []
        while not self.queue.empty():
            try:
                items.append(self.queue.get_nowait())
            except queue.Empty:
                break
        return items
        
    def empty(self):
        """Check if queue is empty"""
        return self.queue.empty()
        
    def get_nowait(self):
        """Get item without waiting"""
        return self.queue.get_nowait()


class PeriodicTimer:
    """Periodic timer that calls a function at regular intervals"""
    
    def __init__(self, interval: float, callback: Callable):
        self.interval = interval
        self.callback = callback
        self.timer = None
        self.running = False
        
    def start(self):
        """Start the timer"""
        if not self.running:
            self.running = True
            self._run()
            
    def stop(self):
        """Stop the timer"""
        self.running = False
        if self.timer:
            self.timer.cancel()
            
    def _run(self):
        """Internal run method"""
        if self.running:
            self.callback()
            self.timer = threading.Timer(self.interval, self._run)
            self.timer.start()


def center_window(window: tk.Tk, width: int, height: int):
    """Center window on screen"""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    window.geometry(f'{width}x{height}+{x}+{y}')


def create_tooltip(widget: tk.Widget, text: str):
    """Create a tooltip for a widget"""
    def on_enter(event):
        from .theme import theme
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        tooltip.configure(bg='black')
        
        label = tk.Label(tooltip, text=text, 
                        font=theme.fonts.caption,
                        bg='black', fg='white',
                        padx=5, pady=2)
        label.pack()
        
        # Position tooltip
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + 30
        tooltip.geometry(f'+{x}+{y}')
        
        # Store reference
        widget.tooltip = tooltip
        
    def on_leave(event):
        if hasattr(widget, 'tooltip'):
            widget.tooltip.destroy()
            del widget.tooltip
            
    widget.bind('<Enter>', on_enter)
    widget.bind('<Leave>', on_leave)


# Old theme functions removed - now using centralized theme.py


def safe_call(func: Callable, *args, **kwargs) -> Any:
    """Safely call a function with error handling"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in {func.__name__}: {e}")
        return None


# Duplicate format_time_duration removed - keeping the first one above


def validate_port(port_str: str) -> Optional[int]:
    """Validate port number string"""
    try:
        port = int(port_str)
        if 1024 <= port <= 65535:
            return port
        else:
            return None
    except ValueError:
        return None


class StatusManager:
    """Manages status updates across the application"""
    
    def __init__(self):
        self.callbacks = []
        
    def add_callback(self, callback: Callable[[str, str], None]):
        """Add status update callback"""
        self.callbacks.append(callback)
        
    def update_status(self, message: str, status_type: str = 'info'):
        """Update status across all registered callbacks"""
        for callback in self.callbacks:
            try:
                callback(message, status_type)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")


# Global status manager instance
status_manager = StatusManager()


def format_bytes(bytes_count: int) -> str:
    """Format bytes to human readable string"""
    if bytes_count == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(bytes_count)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def format_frequency(hz: float) -> str:
    """Format frequency in Hz to human readable string"""
    if hz >= 1000000:
        return f"{hz/1000000:.1f} MHz"
    elif hz >= 1000:
        return f"{hz/1000:.1f} kHz"
    else:
        return f"{hz:.0f} Hz"


def format_percentage(value: float, total: float) -> str:
    """Format percentage with proper handling of zero division"""
    if total == 0:
        return "0%"
    percentage = (value / total) * 100
    return f"{percentage:.1f}%"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length with suffix"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_timestamp(timestamp: float, format_str: str = "%H:%M:%S") -> str:
    """Format timestamp to readable string"""
    import time
    return time.strftime(format_str, time.localtime(timestamp))


def parse_version_string(version_str: str) -> tuple:
    """Parse version string into tuple of integers"""
    try:
        return tuple(map(int, version_str.split('.')))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    return max(min_val, min(value, max_val))


def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(url))


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    import os
    return os.path.splitext(filename)[1].lower()


def ensure_directory(directory_path: str) -> bool:
    """Ensure directory exists, create if needed"""
    import os
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory_path}: {e}")
        return False


class AsyncTaskManager:
    """Manages async tasks for GUI operations"""
    
    def __init__(self):
        self.tasks = {}
        self.task_counter = 0
    
    def run_task(self, func: Callable, callback: Optional[Callable] = None, 
                 error_callback: Optional[Callable] = None) -> str:
        """Run function in background thread with optional callbacks"""
        task_id = f"task_{self.task_counter}"
        self.task_counter += 1
        
        def task_wrapper():
            try:
                result = func()
                if callback:
                    callback(result)
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                if error_callback:
                    error_callback(e)
            finally:
                if task_id in self.tasks:
                    del self.tasks[task_id]
        
        thread = threading.Thread(target=task_wrapper, daemon=True)
        self.tasks[task_id] = thread
        thread.start()
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task (note: Python threads can't be forcibly stopped)"""
        if task_id in self.tasks:
            # We can't actually stop the thread, just remove the reference
            del self.tasks[task_id]
            return True
        return False
    
    def get_active_tasks(self) -> list:
        """Get list of active task IDs"""
        return list(self.tasks.keys())


# Global async task manager
task_manager = AsyncTaskManager()
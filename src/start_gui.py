#!/usr/bin/env python3
"""
Startup script for VTuber GUI application
"""

import sys
import os
import subprocess
import threading
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def start_backend():
    """Start the FastAPI backend"""
    print("Starting FastAPI backend...")
    try:
        # Change to backend directory and start the server
        backend_dir = project_root / "backend"
        os.chdir(backend_dir)
        
        # Start the backend server
        subprocess.run([sys.executable, "main.py"])
    except Exception as e:
        print(f"Error starting backend: {e}")
        return False
    return True

def start_gui():
    """Start the Tkinter GUI"""
    print("Starting Tkinter GUI...")
    try:
        from frontend.gui import main
        main()
    except Exception as e:
        print(f"Error starting GUI: {e}")
        return False
    return True

def main():
    """Main entry point"""
    print("VTuber Backend - Startup Script")
    print("================================")
    
    # Check if we're starting backend or GUI
    if len(sys.argv) > 1 and sys.argv[1] == "backend":
        # Start backend only
        start_backend()
    elif len(sys.argv) > 1 and sys.argv[1] == "gui":
        # Start GUI only
        start_gui()
    else:
        # Start both in separate threads
        print("Starting both backend and GUI...")
        
        # Start backend in a separate thread
        backend_thread = threading.Thread(target=start_backend, daemon=True)
        backend_thread.start()
        
        # Wait a bit for backend to start
        print("Waiting for backend to start...")
        time.sleep(3)
        
        # Start GUI
        start_gui()

if __name__ == "__main__":
    main()
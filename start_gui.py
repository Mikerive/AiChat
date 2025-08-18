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

# Add the project root and frontend directory to Python path so imports like
# "from components..." inside frontend modules resolve correctly when running
# the startup script from the repository root.
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
# Also add the frontend package directory so top-level "components" imports work
frontend_dir = project_root / "frontend"
if str(frontend_dir) not in sys.path:
    sys.path.insert(0, str(frontend_dir))

def start_backend():
    """Start the FastAPI backend as a subprocess without changing the current working directory.

    This avoids altering the interpreter's global cwd (which breaks imports for the GUI).
    We run the backend as a module from the project root so 'backend' is importable.
    """
    print("Starting FastAPI backend...")
    try:
        # Run backend as a module from the project root so package imports resolve.
        proc = subprocess.Popen(
            [sys.executable, "-m", "backend.main"],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        print(f"Backend started (pid={proc.pid})")
    except Exception as e:
        print(f"Error starting backend: {e}")
        return False
    return True

def start_gui():
    """Start the Tkinter GUI in a separate process to avoid import side-effects
    that can create unintended secondary windows when modules are imported into
    the current interpreter."""
    print("Starting Tkinter GUI (separate process)...")
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "frontend.gui"],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        print(f"GUI started (pid={proc.pid})")
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
#!/usr/bin/env python3
"""
GUI startup script for VTuber application
Run this after starting the backend with start_backend.py
"""

import os
import sys
from pathlib import Path

def main():
    """Start the GUI application"""
    print("VTuber GUI Startup Script")
    print("=" * 40)
    
    # Get the project root directory
    script_dir = Path(__file__).parent
    src_dir = script_dir / "src" if (script_dir / "src").exists() else script_dir
    
    print(f"Working directory: {src_dir}")
    
    # Change to the source directory
    os.chdir(src_dir)
    
    try:
        print("Starting GUI...")
        print("   Make sure the backend server is running first!")
        print("-" * 40)
        
        # Import and start the GUI
        sys.path.insert(0, str(src_dir))
        from frontend.gui import main as gui_main
        gui_main()
        
    except ImportError as e:
        print(f"\nImport error: {e}")
        print("Make sure all dependencies are installed:")
        print("   pip install -r requirements.txt")
    except Exception as e:
        print(f"\nError starting GUI: {e}")
    
    print("\nGUI application finished")

if __name__ == "__main__":
    main()
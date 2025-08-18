#!/usr/bin/env python3
"""
Backend startup script for VTuber application
Run this in a separate terminal to start the backend services
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the backend server"""
    print("VTuber Backend Startup Script")
    print("=" * 50)
    
    # Get the project root directory
    script_dir = Path(__file__).parent
    src_dir = script_dir / "src" if (script_dir / "src").exists() else script_dir
    
    print(f"Working directory: {src_dir}")
    
    # Change to the source directory
    os.chdir(src_dir)
    
    try:
        print("Starting backend server...")
        print("   Using: uvicorn backend.chat_app.main:create_app --factory --host localhost --port 8765")
        print("   Press Ctrl+C to stop the server")
        print("-" * 50)
        
        # Start the backend server using uvicorn
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "backend.chat_app.main:create_app", 
            "--factory", 
            "--host", "localhost", 
            "--port", "8765",
            "--reload"  # Enable auto-reload for development
        ], check=True)
        
    except KeyboardInterrupt:
        print("\n\nBackend server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\nError starting backend server: {e}")
        print("Make sure all dependencies are installed:")
        print("   pip install -r requirements.txt")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    
    print("\nBackend startup script finished")

if __name__ == "__main__":
    main()
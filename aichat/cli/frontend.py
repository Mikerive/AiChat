"""
Frontend CLI entry point - Streamlit Official Interface
"""

from argparse import Namespace
import sys
import subprocess
from pathlib import Path


def main(args: Namespace = None):
    """Start the GUI frontend (Streamlit by default)"""
    gui_type = getattr(args, 'gui', 'streamlit') if args else 'streamlit'
    
    print(f"[VTUBER] Starting VTuber Control Center ({gui_type.upper()})")
    print("Official Interface - Modern, Fast, and Actually Works")
    print("-" * 60)

    try:
        if gui_type == "streamlit":
            # Use Streamlit web interface (default)
            streamlit_app = Path(__file__).parent.parent / "frontend" / "streamlit_app.py"
            
            if not streamlit_app.exists():
                print(f"[ERROR] Streamlit app not found at: {streamlit_app}")
                return 1
                
            print("[LAUNCH] Starting Streamlit interface...")
            print("[WEB] Web Interface: http://localhost:8501")
            print("[FEATURES] Real-time monitoring, Backend control, TTS & Chat")
            print("[ENHANCED] Auto-refresh, Session management, Professional UI")
            print("-" * 60)
            
            # Start Streamlit
            result = subprocess.run([
                sys.executable, "-m", "streamlit", "run",
                str(streamlit_app),
                "--server.port", "8501",
                "--browser.gatherUsageStats", "false"
            ])
            
            return result.returncode
            
        else:
            print(f"[ERROR] GUI type '{gui_type}' not supported.")
            print("[AVAILABLE] streamlit (default)")
            print("[INFO] Legacy PyGui and Tkinter interfaces have been removed.")
            print("       Streamlit provides a superior web-based interface.")
            return 1
            
    except ImportError as e:
        print(f"[ERROR] Error importing {gui_type} frontend: {e}")
        if gui_type == "streamlit":
            print("[HELP] Try: pip install streamlit")
        return 1
    except Exception as e:
        print(f"[ERROR] Error starting {gui_type} frontend: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

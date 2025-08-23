#!/usr/bin/env python3
"""
Debug why backend process crashes immediately
"""

import sys
import time
import subprocess
from pathlib import Path

def debug_backend_crash():
    """Debug backend startup and capture crash details"""
    print("[DEBUG] Backend Crash Investigation")
    print("=" * 50)
    
    try:
        # Start backend and capture ALL output
        print("[START] Starting backend with full output capture...")
        
        process = subprocess.Popen([
            sys.executable, "-m", "aichat.cli.main", 
            "backend", "--host", "localhost", 
            "--port", "8765"
        ], cwd=Path.cwd(), 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,  # Combine stderr into stdout
        text=True,
        bufsize=1,
        universal_newlines=True)
        
        print(f"[PID] Started process: {process.pid}")
        
        # Monitor for 10 seconds
        start_time = time.time()
        output_lines = []
        
        while time.time() - start_time < 10:
            # Check if process ended
            poll_result = process.poll()
            if poll_result is not None:
                print(f"[CRASH] Process exited with code: {poll_result}")
                break
                
            # Read any available output
            try:
                line = process.stdout.readline()
                if line:
                    output_lines.append(line.strip())
                    print(f"[OUT] {line.strip()}")
            except:
                pass
                
            time.sleep(0.1)
        
        # Get remaining output
        try:
            remaining_output, _ = process.communicate(timeout=2)
            if remaining_output:
                for line in remaining_output.split('\n'):
                    if line.strip():
                        output_lines.append(line.strip())
                        print(f"[FINAL] {line.strip()}")
        except:
            pass
        
        # Kill if still running
        if process.poll() is None:
            process.terminate()
            
        print(f"\n[SUMMARY] Process exit code: {process.returncode}")
        print(f"[SUMMARY] Total output lines: {len(output_lines)}")
        
        # Look for errors in output
        error_lines = [line for line in output_lines if 'error' in line.lower() or 'exception' in line.lower() or 'traceback' in line.lower()]
        if error_lines:
            print("\n[ERRORS] Found error indicators:")
            for error in error_lines:
                print(f"  - {error}")
        
        return process.returncode == 0
        
    except Exception as e:
        print(f"[ERROR] Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_backend_crash()
#!/usr/bin/env python3
"""
Debug script to monitor frontend backend startup in real-time
"""

import sys
import time
import subprocess
import threading
from pathlib import Path

def read_output(pipe, label):
    """Read output from subprocess pipe in real-time"""
    for line in iter(pipe.readline, b''):
        try:
            print(f"[{label}] {line.decode('utf-8', errors='ignore').rstrip()}")
        except:
            print(f"[{label}] <encoding error>")
    pipe.close()

def test_realtime_startup():
    """Test backend startup with real-time output monitoring"""
    print("[DEBUG] Real-time Backend Startup Test")
    print("=" * 50)
    
    api_host = "localhost"
    api_port = 8767  # Use different port to avoid conflicts
    
    try:
        print(f"[START] Starting backend on {api_host}:{api_port}")
        
        # Start process without capturing output initially
        process = subprocess.Popen([
            sys.executable, "-m", "aichat.cli.main", 
            "backend", "--host", api_host, 
            "--port", str(api_port)  # Remove --reload to see if that helps
        ], cwd=Path.cwd(), 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0)
        
        print(f"[PID] Process started with PID: {process.pid}")
        
        # Start threads to read output in real-time
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, "OUT"))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, "ERR"))
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Monitor the process for up to 30 seconds
        for i in range(30):
            poll_result = process.poll()
            if poll_result is not None:
                print(f"[EXIT] Process exited with code: {poll_result}")
                break
                
            # Test connectivity every 3 seconds after first 9 seconds
            if i >= 9 and i % 3 == 0:
                try:
                    import requests
                    response = requests.get(f"http://{api_host}:{api_port}/api/system/status", timeout=2)
                    print(f"[API] Backend responding: HTTP {response.status_code}")
                    print(f"[SUCCESS] Backend is accessible!")
                    break
                except Exception as api_e:
                    print(f"[API] Not ready yet: {type(api_e).__name__}")
            
            time.sleep(1)
        
        # Clean up
        if process.poll() is None:
            print("[CLEANUP] Terminating process...")
            process.terminate()
            process.wait(timeout=5)
        
        # Wait for threads to finish
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        
        print("[DONE] Test completed")
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_realtime_startup()
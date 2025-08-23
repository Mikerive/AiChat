#!/usr/bin/env python3
"""
Test the improved backend startup logic
"""

import sys
import time
import subprocess
import requests
from pathlib import Path

def test_improved_startup():
    """Test improved startup with proper waiting and monitoring"""
    print("[IMPROVED] Testing Enhanced Frontend Startup Logic")
    print("=" * 60)
    
    api_host = "localhost"
    api_port = 8768
    
    try:
        # Start the process
        print(f"[START] Starting backend on {api_host}:{api_port}")
        
        process = subprocess.Popen([
            sys.executable, "-m", "aichat.cli.main", 
            "backend", "--host", api_host, 
            "--port", str(api_port)
        ], cwd=Path.cwd(), 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0)
        
        print(f"[PID] Backend starting (PID: {process.pid})")
        
        # Simulate the improved waiting logic
        api_url = f"http://{api_host}:{api_port}"
        startup_success = False
        
        for i in range(20):  # Wait up to 20 seconds
            try:
                # Check if process is still running
                if process.poll() is not None:
                    print(f"[FAIL] Backend process exited unexpectedly with code {process.poll()}")
                    stdout, stderr = process.communicate()
                    print("[STDOUT]", stdout.decode('utf-8', errors='ignore')[:300])
                    print("[STDERR]", stderr.decode('utf-8', errors='ignore')[:300])
                    return False
                
                # Show progress
                print(f"[WAIT] Starting... {i+1}/20s")
                
                # Test connectivity after 8 seconds
                if i >= 8:
                    try:
                        response = requests.get(f"{api_url}/api/system/status", timeout=2)
                        if response.status_code == 200:
                            print("[SUCCESS] Backend ready and responding!")
                            startup_success = True
                            break
                    except Exception as e:
                        print(f"[WAIT] Not ready yet: {type(e).__name__}")
                
                time.sleep(1)
            except Exception as e:
                print(f"[ERROR] Monitoring error: {e}")
        
        # Clean up
        if process.poll() is None:
            print("[CLEANUP] Stopping backend...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        
        if startup_success:
            print("[RESULT] ✅ Improved startup logic works!")
            return True
        else:
            print("[RESULT] ❌ Backend didn't become ready in time")
            return False
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

if __name__ == "__main__":
    test_improved_startup()
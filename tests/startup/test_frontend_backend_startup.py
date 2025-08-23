#!/usr/bin/env python3
"""
Test script to simulate frontend backend startup and capture errors
"""

import sys
import time
import subprocess
from pathlib import Path

def test_frontend_backend_startup():
    """Test backend startup exactly as the frontend does it"""
    print("[TEST] Simulating Frontend Backend Startup")
    print("=" * 50)
    
    # Simulate the exact command that Streamlit GUI uses
    api_host = "localhost"
    api_port = 8765
    
    try:
        print(f"[START] Starting backend on {api_host}:{api_port}")
        
        # This is the exact code from streamlit_app.py
        process = subprocess.Popen([
            sys.executable, "-m", "aichat.cli.main", 
            "backend", "--host", api_host, 
            "--port", str(api_port), "--reload"
        ], cwd=Path.cwd(), 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0)
        
        print(f"[PID] Process started with PID: {process.pid}")
        
        # Wait a bit for startup
        time.sleep(5)
        
        # Check if process is still running
        poll_result = process.poll()
        if poll_result is None:
            print("[RUNNING] Process is still running")
            
            # Try to communicate with it
            import requests
            try:
                response = requests.get(f"http://{api_host}:{api_port}/api/system/status", timeout=5)
                print(f"[API] Backend responding: HTTP {response.status_code}")
            except Exception as api_e:
                print(f"[API] Backend not responding: {api_e}")
            
            # Kill the process
            process.terminate()
            process.wait(timeout=5)
            print("[STOP] Process terminated")
            
        else:
            print(f"[FAILED] Process exited with code: {poll_result}")
            
            # Get the output
            stdout, stderr = process.communicate()
            
            print("\n[STDOUT]")
            print(stdout.decode('utf-8', errors='ignore'))
            
            print("\n[STDERR]")
            print(stderr.decode('utf-8', errors='ignore'))
        
        return poll_result == 0 or poll_result is None
        
    except Exception as e:
        print(f"[ERROR] Failed to start backend: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manual_startup():
    """Test if manual startup works"""
    print("\n[MANUAL] Testing manual backend startup")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "aichat.cli.main", 
            "backend", "--host", "localhost", 
            "--port", "8766", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        print(f"[HELP] Backend help command exit code: {result.returncode}")
        if result.stdout:
            print("[HELP OUTPUT]")
            print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
        if result.stderr:
            print("[HELP STDERR]")  
            print(result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("[TIMEOUT] Command timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Manual test failed: {e}")
        return False

if __name__ == "__main__":
    print("Frontend Backend Startup Test")
    print("=" * 60)
    
    # Test 1: Help command to verify CLI works
    manual_ok = test_manual_startup()
    
    # Test 2: Actual startup simulation
    if manual_ok:
        startup_ok = test_frontend_backend_startup()
        
        if startup_ok:
            print("\n[SUCCESS] Frontend backend startup should work")
        else:
            print("\n[FAILURE] Frontend backend startup has issues")
    else:
        print("\n[SKIP] CLI issues detected, skipping startup test")
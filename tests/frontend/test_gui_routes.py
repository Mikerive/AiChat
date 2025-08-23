#!/usr/bin/env python3
"""
GUI Route Testing Script

Tests all API routes that the GUI uses to ensure backend connectivity
and proper response handling.
"""

import sys
import time
from pathlib import Path
from aichat.frontend.api_client import VTuberAPIClient

def test_api_routes(client: VTuberAPIClient):
    """Test all API routes used by the GUI"""
    
    print("[TEST] Testing VTuber GUI API Routes")
    print("=" * 50)
    
    results = []
    
    # Test system routes
    print("\n[SYSTEM] System Routes:")
    test_cases = [
        ("System Status", lambda: client.get_system_status()),
        ("System Info", lambda: client.get_system_info()),
        ("Connection Test", lambda: client.test_connection()),
    ]
    
    for name, test_func in test_cases:
        try:
            result = test_func()
            print(f"  [OK] {name}: PASS")
            results.append((name, "PASS", result))
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            results.append((name, "FAIL", str(e)))
    
    # Test chat routes
    print("\n[CHAT] Chat Routes:")
    chat_tests = [
        ("Get Characters", lambda: client.get_characters()),
        ("Send Chat Message", lambda: client.send_chat_message("Hello test")),
        ("Generate TTS", lambda: client.generate_tts("Hello world")),
    ]
    
    for name, test_func in chat_tests:
        try:
            result = test_func()
            print(f"  [OK] {name}: PASS")
            results.append((name, "PASS", result))
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            results.append((name, "FAIL", str(e)))
    
    # Test audio routes
    print("\n[AUDIO] Audio Routes:")
    audio_tests = [
        ("Get Audio Devices", lambda: client.get_audio_devices()),
        ("Get Audio Status", lambda: client.get_audio_status()),
        # Skip hardware-dependent tests by default
        # ("Record Audio", lambda: client.record_audio(1.0)),
        # ("Set Volume", lambda: client.set_volume(0.5)),
    ]
    
    for name, test_func in audio_tests:
        try:
            result = test_func()
            print(f"  [OK] {name}: PASS")
            results.append((name, "PASS", result))
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            results.append((name, "FAIL", str(e)))
    
    # Health check
    print("\n[HEALTH] Health Check:")
    try:
        health = client.health_check()
        print(f"  [OK] Comprehensive Health Check: PASS")
        results.append(("Health Check", "PASS", health))
    except Exception as e:
        print(f"  [FAIL] Comprehensive Health Check: {e}")
        results.append(("Health Check", "FAIL", str(e)))
    
    # Summary
    print("\n[SUMMARY] Test Summary:")
    print("=" * 50)
    passed = sum(1 for _, status, _ in results if status == "PASS")
    total = len(results)
    
    for name, status, result in results:
        status_icon = "[OK]" if status == "PASS" else "[FAIL]"
        print(f"  {status_icon} {name}: {status}")
    
    print(f"\n[RESULT] Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    return results

def main():
    """Main test runner"""
    
    # Test different common ports
    ports_to_test = [8765, 8766, 8888, 9000]
    
    print("[START] VTuber GUI API Route Tester")
    print("Searching for running backend...")
    
    client = None
    working_port = None
    
    # Find working backend
    for port in ports_to_test:
        test_client = VTuberAPIClient(f"http://localhost:{port}")
        try:
            if test_client.test_connection():
                print(f"[FOUND] Backend running on port {port}")
                client = test_client
                working_port = port
                break
        except:
            continue
    
    if not client:
        print("[ERROR] No backend found on common ports")
        print("Please start the backend first:")
        print("  python -m aichat.cli.main backend --host localhost --port 8765")
        return 1
    
    # Run tests
    print(f"\n[CONNECT] Testing backend at http://localhost:{working_port}")
    results = test_api_routes(client)
    
    # Check if any critical routes failed
    critical_routes = ["System Status", "Connection Test", "Get Audio Devices"]
    critical_failures = [
        name for name, status, _ in results 
        if name in critical_routes and status == "FAIL"
    ]
    
    if critical_failures:
        print(f"\n[WARNING] Critical route failures detected: {critical_failures}")
        print("GUI may not function properly")
        return 1
    else:
        print(f"\n[SUCCESS] All critical routes working! GUI should function properly")
        return 0

if __name__ == "__main__":
    sys.exit(main())
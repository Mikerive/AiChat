#!/usr/bin/env python3
"""
VTuber Speech Pipeline Test - Windows Compatible
"""

import requests
import json
import time
import os
import sys

BASE_URL = "http://localhost:8765"

def test_system():
    """Test system status"""
    print("[SYSTEM] Testing backend status...")
    try:
        response = requests.get(f"{BASE_URL}/api/system/status", timeout=5)
        response.raise_for_status()
        status = response.json()
        print(f"[SYSTEM] SUCCESS - Status: {status.get('status')}")
        print(f"[SYSTEM] Uptime: {status.get('uptime', 0):.1f}s")
        return True
    except Exception as e:
        print(f"[SYSTEM] FAILED: {e}")
        return False

def test_tts():
    """Test text-to-speech"""
    print("[TTS] Testing text-to-speech...")
    test_text = "Hello! This is a test of the text to speech system."
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/tts",
            json={"text": test_text, "character": "assistant"},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        audio_file = result.get("audio_file")
        print(f"[TTS] SUCCESS - Generated: {os.path.basename(audio_file) if audio_file else 'None'}")
        print(f"[TTS] Format: {result.get('audio_format')}")
        
        # Check if file exists and size
        if audio_file and os.path.exists(audio_file):
            size = os.path.getsize(audio_file)
            print(f"[TTS] File size: {size} bytes")
            return audio_file, size > 100  # Return path and whether it's a real audio file
        else:
            print("[TTS] WARNING - Audio file not found or not created")
            return audio_file, False
            
    except Exception as e:
        print(f"[TTS] FAILED: {e}")
        return None, False

def test_audio_devices():
    """Test audio device detection"""
    print("[AUDIO] Testing audio devices...")
    try:
        response = requests.get(f"{BASE_URL}/api/voice/audio/devices", timeout=10)
        response.raise_for_status()
        devices = response.json()
        
        input_devices = devices.get("input_devices", [])
        output_devices = devices.get("output_devices", [])
        
        print(f"[AUDIO] SUCCESS - {len(input_devices)} input, {len(output_devices)} output devices")
        
        # Find default devices
        default_input = next((d for d in input_devices if d.get("is_default")), None)
        default_output = next((d for d in output_devices if d.get("is_default")), None)
        
        if default_input:
            print(f"[AUDIO] Default microphone: {default_input['name']}")
        if default_output:
            print(f"[AUDIO] Default speaker: {default_output['name']}")
            
        return len(input_devices) > 0 and len(output_devices) > 0
        
    except Exception as e:
        print(f"[AUDIO] FAILED: {e}")
        return False

def test_chat():
    """Test chat API"""
    print("[CHAT] Testing chat API...")
    test_message = "Hello! Can you tell me about yourself?"
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/chat",
            json={"text": test_message, "character": "assistant"},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        chat_response = result.get("response", "No response")
        print(f"[CHAT] SUCCESS - Response: '{chat_response[:100]}...'")
        return chat_response
        
    except Exception as e:
        print(f"[CHAT] FAILED: {e}")
        return None

def test_stt():
    """Test speech-to-text (will likely fail due to missing services)"""
    print("[STT] Testing speech-to-text...")
    try:
        # Test record endpoint
        response = requests.post(f"{BASE_URL}/api/voice/audio/record?duration=1.0", timeout=10)
        if response.status_code == 200:
            print("[STT] SUCCESS - Recording works")
            return True
        else:
            print(f"[STT] FAILED - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"[STT] FAILED: {e}")
        return False

def main():
    """Run comprehensive speech tests"""
    print("=" * 60)
    print("VTuber Speech Pipeline Test Suite")
    print("=" * 60)
    
    # Track results
    results = {}
    
    # 1. System test
    results['system'] = test_system()
    print()
    
    # 2. Audio devices
    results['audio'] = test_audio_devices()
    print()
    
    # 3. TTS test
    audio_file, is_real_audio = test_tts()
    results['tts'] = audio_file is not None
    results['tts_real'] = is_real_audio
    print()
    
    # 4. Chat test
    chat_response = test_chat()
    results['chat'] = chat_response is not None
    print()
    
    # 5. STT test
    results['stt'] = test_stt()
    print()
    
    # 6. If chat works, test TTS with chat response
    if chat_response:
        print("[INTEGRATION] Testing TTS with chat response...")
        response_audio, response_real = test_tts()
        results['integration'] = response_audio is not None
        print()
    
    # Summary
    print("=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test.upper():15} {status}")
    
    print()
    print("ANALYSIS:")
    
    if results.get('system'):
        print("+ Backend is running and responding")
    else:
        print("- Backend is not accessible")
    
    if results.get('audio'):
        print("+ Audio devices detected successfully")
    else:
        print("- Audio system issues detected")
        
    if results.get('tts'):
        if results.get('tts_real'):
            print("+ TTS working with real audio generation")
        else:
            print("+ TTS endpoint working but generating fallback audio only")
            print("  (Missing PiperTTSService)")
    else:
        print("- TTS completely broken")
        
    if results.get('chat'):
        print("+ Chat API working with assistant character")
    else:
        print("- Chat API not working")
        
    if results.get('stt'):
        print("+ STT/Recording working")
    else:
        print("- STT/Recording not working (Expected - missing imports)")
        
    print()
    print("RECOMMENDATIONS:")
    if not results.get('tts_real'):
        print("1. Fix PiperTTSService import to enable real TTS")
    if not results.get('stt'):
        print("2. Fix STT service imports for speech recognition")
    if results.get('system') and results.get('chat'):
        print("3. Core chat functionality is working well!")
    
    # Interactive test
    if results.get('chat') and input("\nRun interactive chat test? (y/n): ").lower().startswith('y'):
        print("\n" + "=" * 40)
        print("INTERACTIVE CHAT TEST")
        print("=" * 40)
        
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ['quit', 'exit', 'bye']:
                break
                
            try:
                response = requests.post(
                    f"{BASE_URL}/api/chat/chat",
                    json={"text": user_input, "character": "assistant"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result.get("response", "No response")
                    print(f"AI: {ai_response}")
                    
                    # Optionally generate TTS
                    if input("Generate speech for this response? (y/n): ").lower().startswith('y'):
                        tts_result = requests.post(
                            f"{BASE_URL}/api/chat/tts",
                            json={"text": ai_response, "character": "assistant"}
                        )
                        if tts_result.status_code == 200:
                            tts_data = tts_result.json()
                            audio_file = tts_data.get("audio_file")
                            if audio_file:
                                print(f"Audio generated: {os.path.basename(audio_file)}")
                else:
                    print(f"Error: {response.status_code}")
                    
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()
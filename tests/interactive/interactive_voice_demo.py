#!/usr/bin/env python3
"""
Interactive Voice Demo - What Currently Works
"""

import requests
import time
import os

def demo_tts_responses():
    """Demo TTS with various response types"""
    print("=" * 50)
    print("TTS (Text-to-Speech) Demo")
    print("=" * 50)
    
    demo_messages = [
        ("Welcome", "Welcome to the VTuber voice interface! I'm your AI assistant."),
        ("Instruction", "To test the voice system, I'll speak different types of messages."),
        ("User Simulation", "This is how I would respond to user input."),
        ("System Status", "All systems are operational. Backend is running normally."),
        ("Voice Pipeline", "The voice pipeline includes speech recognition, chat processing, and speech synthesis."),
        ("Current Limitations", "Currently, I'm using fallback audio generation. Full speech synthesis requires additional service setup."),
        ("Future Capabilities", "Once fully configured, I'll be able to provide high-quality voice responses with emotional expression.")
    ]
    
    print("The system will generate TTS audio for each message:")
    print()
    
    for title, message in demo_messages:
        print(f"[{title}] {message}")
        
        try:
            response = requests.post(
                "http://localhost:8765/api/chat/tts",
                json={"text": message, "character": "assistant"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                audio_file = result.get("audio_file", "")
                filename = os.path.basename(audio_file) if audio_file else "None"
                print(f"    -> Audio generated: {filename}")
            else:
                print(f"    -> TTS failed: {response.status_code}")
                
        except Exception as e:
            print(f"    -> Error: {e}")
            
        print()
        time.sleep(1)
    
    return True

def demo_gui_interaction():
    """Demo what the GUI interaction would look like"""
    print("=" * 50)
    print("GUI Voice Interaction Demo")
    print("=" * 50)
    
    print("Here's what the GUI voice interface can do:")
    print()
    
    # Simulate GUI workflow
    scenarios = [
        {
            "action": "User clicks 'Hold to Talk' button",
            "result": "Microphone activates (currently blocked by STT import issues)"
        },
        {
            "action": "User types: 'Hello, how are you?'",
            "result": "Message appears left-aligned in chat display"
        },
        {
            "action": "System processes chat request", 
            "result": "Backend generates AI response (currently has validation issues)"
        },
        {
            "action": "AI response received",
            "result": "Message appears right-aligned in chat display"
        },
        {
            "action": "User clicks 'Generate Speech'",
            "result": "TTS converts response to audio (fallback mode working)"
        },
        {
            "action": "Audio playback",
            "result": "Response plays through speakers"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['action']}")
        print(f"   Result: {scenario['result']}")
        print()
        time.sleep(0.5)
    
    return True

def demo_system_capabilities():
    """Demo current system capabilities"""
    print("=" * 50)
    print("System Capabilities Demo")
    print("=" * 50)
    
    capabilities = []
    
    # Test system status
    try:
        response = requests.get("http://localhost:8765/api/system/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            capabilities.append(f"✓ Backend Status: {status.get('status', 'Unknown')}")
            capabilities.append(f"✓ Uptime: {status.get('uptime', 0):.1f} seconds")
            capabilities.append(f"✓ Services: {', '.join(status.get('services', {}).keys())}")
        else:
            capabilities.append("✗ Backend not responding")
    except Exception as e:
        capabilities.append(f"✗ Backend error: {e}")
    
    # Test audio devices
    try:
        response = requests.get("http://localhost:8765/api/voice/audio/devices", timeout=5)
        if response.status_code == 200:
            devices = response.json()
            input_count = len(devices.get("input_devices", []))
            output_count = len(devices.get("output_devices", []))
            capabilities.append(f"✓ Audio Devices: {input_count} input, {output_count} output")
        else:
            capabilities.append("✗ Audio devices not accessible")
    except Exception as e:
        capabilities.append(f"✗ Audio error: {e}")
    
    # Test TTS
    try:
        response = requests.post(
            "http://localhost:8765/api/chat/tts",
            json={"text": "Capability test", "character": "assistant"},
            timeout=10
        )
        if response.status_code == 200:
            capabilities.append("✓ TTS Generation: Working (fallback mode)")
        else:
            capabilities.append("✗ TTS Generation: Failed")
    except Exception as e:
        capabilities.append(f"✗ TTS error: {e}")
    
    print("Current System Status:")
    for capability in capabilities:
        print(f"  {capability}")
    
    print()
    
    known_issues = [
        "STT Services: Missing import paths",
        "PiperTTS Service: Module not found", 
        "OpenRouter Service: Module not found",
        "Chat API: Response validation errors",
        "Audio Recording: Missing time import"
    ]
    
    print("Known Issues to Fix:")
    for issue in known_issues:
        print(f"  ⚠ {issue}")
    
    print()
    
    return len([c for c in capabilities if c.startswith("✓")]) > 0

def interactive_demo():
    """Run interactive demonstration"""
    print("VTuber Voice Interface - Interactive Demo")
    print("=" * 60)
    print()
    
    demos = [
        ("TTS Demo", demo_tts_responses),
        ("GUI Demo", demo_gui_interaction), 
        ("System Capabilities", demo_system_capabilities)
    ]
    
    for demo_name, demo_func in demos:
        if input(f"Run {demo_name}? (y/n): ").lower().startswith('y'):
            print()
            demo_func()
            input("Press Enter to continue...")
            print()
    
    print("=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)
    print()
    print("What Works Now:")
    print("• Backend API server running")
    print("• Audio device detection")
    print("• TTS audio generation (fallback mode)")
    print("• System status monitoring") 
    print("• GUI chat interface with message alignment")
    print("• Voice controls UI components")
    print()
    print("What Needs Service Fixes:")
    print("• Real speech synthesis (PiperTTSService)")
    print("• Speech recognition (STT services)")
    print("• Full chat API integration")
    print("• Voice recording functionality")
    print()
    print("Next Steps:")
    print("1. Fix missing service import paths")
    print("2. Resolve response validation issues")
    print("3. Test full voice pipeline")
    print("4. Enable real-time voice interaction")

if __name__ == "__main__":
    interactive_demo()
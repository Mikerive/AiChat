#!/usr/bin/env python3
"""
Test script to verify GUI integration and component functionality
"""

import sys
import os
import tkinter as tk
import threading
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test all GUI component imports"""
    print("[TESTING] GUI component imports...")
    
    try:
        # Test core imports
        from aichat.frontend.tkinter.app import VTuberApp
        from aichat.frontend.tkinter.components import (
            CharacterManagerPanel, AudioDevicesPanel, ChatDisplayPanel,
            VoiceControlsPanel, StatusPanel, BackendControlsPanel
        )
        from aichat.frontend.tkinter.models import CharacterProfile, ChatMessage
        from aichat.frontend.tkinter.backend_client import BackendClient
        from aichat.frontend.api_client import VTuberAPIClient
        
        print("[PASS] All imports successful!")
        return True
        
    except ImportError as e:
        print(f"[FAIL] Import failed: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Unexpected error during imports: {e}")
        return False

def test_character_model():
    """Test CharacterProfile model functionality"""
    print("\n[TESTING] CharacterProfile model...")
    
    try:
        from aichat.frontend.tkinter.models import CharacterProfile
        
        # Create test character
        char = CharacterProfile(
            id="test_char",
            name="Test Character",
            description="A test character for validation",
            voice_model="test_voice"
        )
        
        # Test properties
        assert char.display_name == "○ Test Character"
        char.is_active = True
        assert char.display_name == "● Test Character"
        
        # Test serialization
        char_dict = char.to_dict()
        char_restored = CharacterProfile.from_dict(char_dict)
        assert char_restored.name == char.name
        
        print("[PASS] CharacterProfile model working correctly!")
        return True
        
    except Exception as e:
        print(f"[FAIL] CharacterProfile test failed: {e}")
        return False

def test_backend_client():
    """Test BackendClient API integration"""
    print("\n[TESTING] BackendClient API integration...")
    
    try:
        from aichat.frontend.tkinter.backend_client import BackendClient
        
        # Create client (don't actually connect)
        client = BackendClient("http://localhost:8765")
        
        # Test that all required methods exist
        required_methods = [
            'get_characters', 'switch_character', 'get_audio_devices',
            'set_input_device', 'set_output_device', 'get_audio_status',
            'record_audio', 'set_volume', 'generate_tts'
        ]
        
        for method in required_methods:
            if not hasattr(client, method):
                raise AttributeError(f"Missing method: {method}")
        
        print("[PASS] BackendClient has all required methods!")
        return True
        
    except Exception as e:
        print(f"[FAIL] BackendClient test failed: {e}")
        return False

def test_gui_creation():
    """Test GUI creation without showing window"""
    print("\n[TESTING] GUI component creation...")
    
    try:
        # Create root window
        root = tk.Tk()
        root.withdraw()  # Hide window
        
        from aichat.frontend.tkinter.components import (
            CharacterManagerPanel, AudioDevicesPanel
        )
        
        # Test CharacterManagerPanel creation
        char_frame = tk.Frame(root)
        char_panel = CharacterManagerPanel(char_frame)
        
        # Test AudioDevicesPanel creation  
        audio_frame = tk.Frame(root)
        audio_panel = AudioDevicesPanel(audio_frame)
        
        # Cleanup
        root.destroy()
        
        print("[PASS] GUI components created successfully!")
        return True
        
    except Exception as e:
        print(f"[FAIL] GUI creation test failed: {e}")
        return False

def test_api_client_integration():
    """Test VTuberAPIClient integration"""
    print("\n[TESTING] VTuberAPIClient integration...")
    
    try:
        from aichat.frontend.api_client import VTuberAPIClient, create_api_client
        
        # Create API client
        client = create_api_client()
        
        # Test that all required methods exist
        required_methods = [
            'get_system_status', 'get_system_info', 'send_chat_message',
            'generate_tts', 'get_characters', 'get_audio_devices',
            'set_volume', 'get_audio_status'
        ]
        
        for method in required_methods:
            if not hasattr(client, method):
                raise AttributeError(f"Missing method: {method}")
        
        print("[PASS] VTuberAPIClient has all required methods!")
        return True
        
    except Exception as e:
        print(f"[FAIL] VTuberAPIClient test failed: {e}")
        return False

def test_gui_layout():
    """Test complete GUI layout structure"""
    print("\n[TESTING] Complete GUI layout...")
    
    try:
        from aichat.frontend.tkinter.app import VTuberApp
        
        # This will test the complete app creation
        # We'll do it in a separate thread with timeout
        app_created = threading.Event()
        app_error = None
        
        def create_app():
            nonlocal app_error
            try:
                # Create app but don't run mainloop
                app = VTuberApp()
                
                # Verify key components exist
                required_components = [
                    'character_manager', 'chat_display', 'voice_controls',
                    'audio_devices', 'status_panel', 'backend_controls'
                ]
                
                for comp in required_components:
                    if comp not in app.components:
                        raise KeyError(f"Missing component: {comp}")
                
                app_created.set()
                
                # Clean up
                app.root.destroy()
                
            except Exception as e:
                app_error = e
                app_created.set()
        
        # Run app creation in thread with timeout
        thread = threading.Thread(target=create_app, daemon=True)
        thread.start()
        
        # Wait for completion or timeout
        if app_created.wait(timeout=10):
            if app_error:
                raise app_error
            print("[PASS] Complete GUI layout created successfully!")
            return True
        else:
            print("[FAIL] GUI layout test timed out")
            return False
            
    except Exception as e:
        print(f"[FAIL] GUI layout test failed: {e}")
        return False

def run_all_tests():
    """Run all integration tests"""
    print("Starting VTuber GUI Integration Tests\n")
    
    tests = [
        ("Import Tests", test_imports),
        ("Character Model Tests", test_character_model),
        ("Backend Client Tests", test_backend_client),
        ("GUI Creation Tests", test_gui_creation),
        ("API Client Tests", test_api_client_integration),
        ("GUI Layout Tests", test_gui_layout)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"[CRASH] {test_name} crashed: {e}")
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! GUI integration is successful.")
        return True
    else:
        print("Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
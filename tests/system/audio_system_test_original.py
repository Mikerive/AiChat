"""
Comprehensive Audio System Test Suite
Tests TTS output, audio input/output, and complete voice pipeline
"""

import requests
import time
import wave
import numpy as np
from pathlib import Path
import json

BASE_URL = "http://localhost:8765"

def test_tts_variations():
    """Test TTS with different text lengths and content"""
    print("=== TTS OUTPUT TESTS ===")
    
    test_cases = [
        {
            "name": "Short phrase",
            "text": "Hello world.",
            "expected_min_duration": 0.5,
            "expected_max_duration": 2.0
        },
        {
            "name": "Medium sentence", 
            "text": "This is a medium length test sentence for audio generation.",
            "expected_min_duration": 2.0,
            "expected_max_duration": 5.0
        },
        {
            "name": "Long paragraph",
            "text": "This is a much longer test that includes multiple sentences. It should generate a longer audio file with natural speech patterns. The system should handle punctuation properly and create appropriate pauses between sentences.",
            "expected_min_duration": 8.0,
            "expected_max_duration": 15.0
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {case['name']}")
        print(f"  Text: '{case['text'][:60]}{'...' if len(case['text']) > 60 else ''}'")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat/tts",
                json={"text": case["text"], "character": "assistant"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                audio_file = result.get("audio_file")
                
                if audio_file and Path(audio_file).exists():
                    file_path = Path(audio_file)
                    file_size = file_path.stat().st_size
                    
                    # Analyze audio content
                    with wave.open(str(file_path), "rb") as wav:
                        frames = wav.readframes(wav.getnframes())
                        sample_rate = wav.getframerate()
                        channels = wav.getnchannels()
                        
                        if len(frames) > 0:
                            audio_data = np.frombuffer(frames, dtype=np.int16)
                            duration = len(audio_data) / sample_rate
                            non_zero = np.count_nonzero(audio_data)
                            max_amplitude = np.max(np.abs(audio_data))
                            
                            # Check if duration is reasonable
                            duration_ok = case["expected_min_duration"] <= duration <= case["expected_max_duration"]
                            
                            print(f"  PASS - File: {file_path.name}")
                            print(f"  PASS - Size: {file_size:,} bytes")
                            print(f"  PASS - Duration: {duration:.2f}s ({'OK' if duration_ok else 'OUTSIDE EXPECTED RANGE'})")
                            print(f"  PASS - Audio: {non_zero:,}/{len(audio_data):,} non-zero samples")
                            print(f"  PASS - Quality: {sample_rate}Hz, {channels}ch, max amplitude: {max_amplitude}")
                            
                            results.append({
                                "test": case["name"],
                                "success": True,
                                "duration": duration,
                                "file_size": file_size,
                                "has_audio": non_zero > 0,
                                "duration_appropriate": duration_ok
                            })
                        else:
                            print("  FAIL - No audio data in file")
                            results.append({"test": case["name"], "success": False, "error": "No audio data"})
                else:
                    print("  FAIL - Audio file not created or not found")
                    results.append({"test": case["name"], "success": False, "error": "File not found"})
            else:
                print(f"  FAIL - HTTP {response.status_code}: {response.text[:100]}")
                results.append({"test": case["name"], "success": False, "error": f"HTTP {response.status_code}"})
                
        except Exception as e:
            print(f"  FAIL - Exception: {e}")
            results.append({"test": case["name"], "success": False, "error": str(e)})
        
        time.sleep(1)  # Pause between tests
    
    return results

def test_audio_devices():
    """Test audio input/output device detection and configuration"""
    print("\n=== AUDIO DEVICE TESTS ===")
    
    try:
        # Test device enumeration
        response = requests.get(f"{BASE_URL}/api/voice/audio/devices", timeout=10)
        
        if response.status_code == 200:
            devices = response.json()
            input_devices = devices.get("input_devices", [])
            output_devices = devices.get("output_devices", [])
            
            print(f"PASS - Device detection successful")
            print(f"PASS - Input devices: {len(input_devices)}")
            print(f"PASS - Output devices: {len(output_devices)}")
            
            # Show device details
            if input_devices:
                default_input = next((d for d in input_devices if d.get("is_default")), None)
                if default_input:
                    print(f"PASS - Default input: {default_input.get('name', 'Unknown')}")
                    
            if output_devices:
                default_output = next((d for d in output_devices if d.get("is_default")), None) 
                if default_output:
                    print(f"PASS - Default output: {default_output.get('name', 'Unknown')}")
            
            return {
                "success": True,
                "input_count": len(input_devices),
                "output_count": len(output_devices),
                "has_defaults": bool(default_input and default_output)
            }
        else:
            print(f"FAIL - Device detection failed: {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"FAIL - Device test exception: {e}")
        return {"success": False, "error": str(e)}

def test_audio_recording():
    """Test audio input recording functionality"""
    print("\n=== AUDIO RECORDING TESTS ===")
    
    test_durations = [1.0, 3.0, 5.0]  # Test different recording lengths
    results = []
    
    for duration in test_durations:
        print(f"\nRecording test - Duration: {duration}s")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/voice/audio/record",
                params={"duration": duration},
                timeout=duration + 10
            )
            
            if response.status_code == 200:
                result = response.json()
                audio_path = result.get("audio_path")
                recorded_duration = result.get("duration", 0)
                
                if audio_path and Path(audio_path).exists():
                    file_size = Path(audio_path).stat().st_size
                    
                    # Analyze recorded audio
                    with wave.open(audio_path, "rb") as wav:
                        frames = wav.readframes(wav.getnframes())
                        sample_rate = wav.getframerate()
                        
                        if len(frames) > 0:
                            audio_data = np.frombuffer(frames, dtype=np.int16)
                            actual_duration = len(audio_data) / sample_rate
                            
                            duration_match = abs(actual_duration - duration) < 0.5  # Within 0.5s tolerance
                            
                            print(f"  PASS - Recorded: {Path(audio_path).name}")
                            print(f"  PASS - File size: {file_size:,} bytes")
                            print(f"  PASS - Duration: {actual_duration:.2f}s (requested: {duration}s)")
                            print(f"  PASS - Duration match: {'YES' if duration_match else 'NO'}")
                            
                            results.append({
                                "duration_requested": duration,
                                "success": True,
                                "file_size": file_size,
                                "actual_duration": actual_duration,
                                "duration_accurate": duration_match
                            })
                        else:
                            print("  FAIL - No audio data recorded")
                            results.append({"duration_requested": duration, "success": False, "error": "No data"})
                else:
                    print("  FAIL - Recording file not found")
                    results.append({"duration_requested": duration, "success": False, "error": "File not found"})
            else:
                print(f"  FAIL - Recording failed: {response.status_code}")
                results.append({"duration_requested": duration, "success": False, "error": f"HTTP {response.status_code}"})
                
        except Exception as e:
            print(f"  FAIL - Recording exception: {e}")
            results.append({"duration_requested": duration, "success": False, "error": str(e)})
        
        time.sleep(0.5)
    
    return results

def test_complete_voice_pipeline():
    """Test end-to-end voice pipeline: Chat -> TTS -> Audio"""
    print("\n=== COMPLETE VOICE PIPELINE TEST ===")
    
    test_messages = [
        "Tell me a joke",
        "What is artificial intelligence?",
        "How does text-to-speech work?"
    ]
    
    results = []
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nPipeline test {i}: '{message}'")
        
        try:
            # Step 1: Chat
            print("  Step 1: Generating chat response...")
            chat_response = requests.post(
                f"{BASE_URL}/api/chat/chat",
                json={"text": message, "character": "assistant"},
                timeout=30
            )
            
            if chat_response.status_code == 200:
                chat_result = chat_response.json()
                response_text = chat_result.get("response", "")
                print(f"  PASS - Chat response: '{response_text[:60]}...'")
                
                # Step 2: TTS
                print("  Step 2: Converting to speech...")
                tts_response = requests.post(
                    f"{BASE_URL}/api/chat/tts", 
                    json={"text": response_text, "character": "assistant"},
                    timeout=30
                )
                
                if tts_response.status_code == 200:
                    tts_result = tts_response.json()
                    audio_file = tts_result.get("audio_file")
                    
                    if audio_file and Path(audio_file).exists():
                        file_size = Path(audio_file).stat().st_size
                        
                        # Verify audio
                        with wave.open(audio_file, "rb") as wav:
                            frames = wav.readframes(wav.getnframes())
                            if len(frames) > 0:
                                audio_data = np.frombuffer(frames, dtype=np.int16)
                                duration = len(audio_data) / wav.getframerate()
                                non_zero = np.count_nonzero(audio_data)
                                
                                print(f"  PASS - Audio generated: {Path(audio_file).name}")
                                print(f"  PASS - Pipeline complete: Chat -> TTS -> Audio ({duration:.2f}s)")
                                
                                results.append({
                                    "message": message,
                                    "success": True,
                                    "response_length": len(response_text),
                                    "audio_duration": duration,
                                    "has_audio": non_zero > 0
                                })
                            else:
                                print("  FAIL - Generated audio is empty")
                                results.append({"message": message, "success": False, "error": "Empty audio"})
                    else:
                        print("  FAIL - Audio file not created")
                        results.append({"message": message, "success": False, "error": "No audio file"})
                else:
                    print(f"  FAIL - TTS failed: {tts_response.status_code}")
                    results.append({"message": message, "success": False, "error": f"TTS HTTP {tts_response.status_code}"})
            else:
                print(f"  FAIL - Chat failed: {chat_response.status_code}")
                results.append({"message": message, "success": False, "error": f"Chat HTTP {chat_response.status_code}"})
                
        except Exception as e:
            print(f"  FAIL - Pipeline exception: {e}")
            results.append({"message": message, "success": False, "error": str(e)})
        
        time.sleep(1)
    
    return results

def print_summary(tts_results, device_result, recording_results, pipeline_results):
    """Print comprehensive test summary"""
    print("\n" + "="*60)
    print("COMPREHENSIVE AUDIO SYSTEM TEST SUMMARY")
    print("="*60)
    
    # TTS Tests Summary
    tts_passed = sum(1 for r in tts_results if r.get("success", False))
    print(f"TTS OUTPUT TESTS:        {tts_passed}/{len(tts_results)} PASSED")
    
    if tts_results:
        total_duration = sum(r.get("duration", 0) for r in tts_results if r.get("success"))
        print(f"  Total audio generated: {total_duration:.1f}s")
        real_audio = sum(1 for r in tts_results if r.get("has_audio", False))
        print(f"  Real audio files:      {real_audio}/{len(tts_results)}")
    
    # Device Tests Summary
    if device_result.get("success"):
        print(f"DEVICE DETECTION:        PASSED")
        print(f"  Input devices:         {device_result.get('input_count', 0)}")
        print(f"  Output devices:        {device_result.get('output_count', 0)}")
    else:
        print(f"DEVICE DETECTION:        FAILED - {device_result.get('error', 'Unknown')}")
    
    # Recording Tests Summary
    rec_passed = sum(1 for r in recording_results if r.get("success", False))
    print(f"RECORDING TESTS:         {rec_passed}/{len(recording_results)} PASSED")
    
    if recording_results:
        accurate = sum(1 for r in recording_results if r.get("duration_accurate", False))
        print(f"  Duration accuracy:     {accurate}/{len(recording_results)}")
    
    # Pipeline Tests Summary
    pipe_passed = sum(1 for r in pipeline_results if r.get("success", False))
    print(f"VOICE PIPELINE TESTS:    {pipe_passed}/{len(pipeline_results)} PASSED")
    
    # Overall Summary
    total_tests = len(tts_results) + 1 + len(recording_results) + len(pipeline_results)
    total_passed = tts_passed + (1 if device_result.get("success") else 0) + rec_passed + pipe_passed
    
    print(f"\nOVERALL RESULT:          {total_passed}/{total_tests} TESTS PASSED")
    
    if total_passed == total_tests:
        print("STATUS: ALL SYSTEMS FUNCTIONAL!")
    elif total_passed >= total_tests * 0.8:
        print("STATUS: Most systems working, minor issues")
    else:
        print("STATUS: Major issues detected")

def main():
    """Run comprehensive audio system tests"""
    print("COMPREHENSIVE AUDIO SYSTEM TEST SUITE")
    print("Testing TTS, audio I/O, recording, and voice pipeline")
    print("="*60)
    
    # Run all test suites
    tts_results = test_tts_variations()
    device_result = test_audio_devices()
    recording_results = test_audio_recording() 
    pipeline_results = test_complete_voice_pipeline()
    
    # Print comprehensive summary
    print_summary(tts_results, device_result, recording_results, pipeline_results)

if __name__ == "__main__":
    main()
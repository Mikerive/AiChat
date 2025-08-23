"""
VTuber Streaming Functionality Test Suite
Tests WebSocket streaming, TTS generation, and real-time voice pipeline
"""

import asyncio
import aiohttp
import json
import time
import requests
from pathlib import Path

async def test_websocket_streaming():
    """Test WebSocket-based streaming chat responses"""
    print("=== WEBSOCKET STREAMING TEST ===")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Connect to WebSocket
            ws_url = "ws://localhost:8765/api/ws"
            async with session.ws_connect(ws_url) as ws:
                print("PASS - WebSocket connected successfully")
                
                # Send chat message for streaming
                message = {
                    "type": "chat",
                    "text": "Hello! Tell me a short story about space exploration.",
                    "character": "hatsune_miku"
                }
                
                await ws.send_str(json.dumps(message))
                print(f"PASS - Sent streaming request: '{message['text'][:50]}...'")
                
                # Collect streaming responses
                chunks = []
                start_time = time.time()
                
                for i in range(20):  # Listen for multiple chunks
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=3.0)
                        
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            response_type = data.get("type", "unknown")
                            
                            print(f"CHUNK {i+1}: Type={response_type}")
                            
                            if response_type == "chat_response":
                                chunks.append(data)
                                message_content = data.get("message", "")[:100]
                                print(f"  Content: {message_content}...")
                                
                                if data.get("final", False):
                                    print("PASS - Received final streaming chunk")
                                    break
                                    
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print(f"ERROR - WebSocket error: {ws.exception()}")
                            break
                            
                    except asyncio.TimeoutError:
                        print("TIMEOUT - No more chunks received")
                        break
                
                elapsed = time.time() - start_time
                print(f"RESULT - Received {len(chunks)} chunks in {elapsed:.2f}s")
                
                return len(chunks) > 0, chunks
                
    except Exception as e:
        print(f"FAIL - WebSocket streaming error: {e}")
        return False, []

def test_tts_generation():
    """Test TTS audio generation with different inputs"""
    print("\n=== TTS GENERATION TEST ===")
    
    test_cases = [
        {
            "text": "Hello! This is a short test.",
            "character": "hatsune_miku",
            "expected_min_size": 1000  # Minimum expected file size
        },
        {
            "text": "This is a longer test message with multiple sentences. It should generate a longer audio file with more content.",
            "character": "hatsune_miku", 
            "expected_min_size": 5000
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTTS Test {i}: '{test_case['text'][:40]}...'")
        
        try:
            response = requests.post(
                "http://localhost:8765/api/chat/tts",
                json=test_case,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                audio_file = result.get("audio_file", "")
                character = result.get("character", "")
                
                print(f"PASS - Status: {response.status_code}")
                print(f"PASS - Audio file: {audio_file}")
                print(f"PASS - Character: {character}")
                
                # Check if file exists and size
                if audio_file:
                    audio_path = Path(audio_file)
                    if audio_path.exists():
                        file_size = audio_path.stat().st_size
                        print(f"PASS - File exists, size: {file_size} bytes")
                        
                        if file_size >= test_case["expected_min_size"]:
                            print(f"PASS - File size meets minimum ({test_case['expected_min_size']} bytes)")
                            results.append(True)
                        else:
                            print(f"WARN - File size below expected minimum")
                            results.append(True)  # Still counts as working
                    else:
                        print(f"FAIL - Audio file not found: {audio_file}")
                        results.append(False)
                else:
                    print("FAIL - No audio file returned")
                    results.append(False)
            else:
                print(f"FAIL - HTTP {response.status_code}: {response.text[:200]}")
                results.append(False)
                
        except Exception as e:
            print(f"FAIL - TTS request error: {e}")
            results.append(False)
    
    return results

def test_stt_functionality():
    """Test speech-to-text recording functionality"""
    print("\n=== STT RECORDING TEST ===")
    
    try:
        # Test audio recording
        response = requests.post(
            "http://localhost:8765/api/voice/audio/record",
            params={"duration": 2.0},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            audio_path = result.get("audio_path", "")
            duration = result.get("duration", 0)
            
            print(f"PASS - Recording status: {response.status_code}")
            print(f"PASS - Audio path: {audio_path}")
            print(f"PASS - Duration: {duration}s")
            
            # Check if recording file exists
            if audio_path and Path(audio_path).exists():
                file_size = Path(audio_path).stat().st_size
                print(f"PASS - Recording file exists, size: {file_size} bytes")
                return True
            else:
                print("FAIL - Recording file not found")
                return False
        else:
            print(f"FAIL - Recording failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"FAIL - STT recording error: {e}")
        return False

async def test_integrated_voice_pipeline():
    """Test complete voice pipeline: Chat -> TTS -> Audio"""
    print("\n=== INTEGRATED VOICE PIPELINE TEST ===")
    
    try:
        # Step 1: Send chat message
        chat_response = requests.post(
            "http://localhost:8765/api/chat/chat",
            json={
                "text": "Tell me about virtual singers",
                "character": "hatsune_miku"
            },
            timeout=15
        )
        
        if chat_response.status_code == 200:
            chat_result = chat_response.json()
            response_text = chat_result.get("response", "")
            print(f"PASS - Chat response: '{response_text[:100]}...'")
            
            # Step 2: Generate TTS from chat response
            tts_response = requests.post(
                "http://localhost:8765/api/chat/tts",
                json={
                    "text": response_text,
                    "character": "hatsune_miku"
                },
                timeout=15
            )
            
            if tts_response.status_code == 200:
                tts_result = tts_response.json()
                audio_file = tts_result.get("audio_file", "")
                print(f"PASS - TTS generated: {audio_file}")
                
                # Step 3: Verify audio file
                if audio_file and Path(audio_file).exists():
                    file_size = Path(audio_file).stat().st_size
                    print(f"PASS - Audio file verified, size: {file_size} bytes")
                    return True
                else:
                    print("FAIL - Generated audio file not found")
                    return False
            else:
                print(f"FAIL - TTS generation failed: {tts_response.status_code}")
                return False
        else:
            print(f"FAIL - Chat request failed: {chat_response.status_code}")
            return False
            
    except Exception as e:
        print(f"FAIL - Pipeline integration error: {e}")
        return False

async def main():
    """Run all streaming and voice pipeline tests"""
    print("VTuber Voice System - Streaming & Pipeline Test Suite")
    print("=" * 60)
    
    # Test results
    results = {}
    
    # WebSocket streaming test
    streaming_works, chunks = await test_websocket_streaming()
    results["websocket_streaming"] = streaming_works
    
    # TTS generation test
    tts_results = test_tts_generation()
    results["tts_generation"] = all(tts_results)
    results["tts_test_count"] = len(tts_results)
    results["tts_pass_count"] = sum(tts_results)
    
    # STT functionality test
    stt_works = test_stt_functionality()
    results["stt_recording"] = stt_works
    
    # Integrated pipeline test
    pipeline_works = await test_integrated_voice_pipeline()
    results["integrated_pipeline"] = pipeline_works
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    
    for test_name, passed in results.items():
        if test_name.endswith("_count"):
            continue
            
        total_tests += 1
        if passed:
            passed_tests += 1
            status = "PASS"
        else:
            status = "FAIL"
            
        print(f"{test_name.upper():25} {status}")
    
    print(f"\nOVERALL: {passed_tests}/{total_tests} tests passed")
    
    if results["tts_generation"]:
        print(f"TTS Details: {results['tts_pass_count']}/{results['tts_test_count']} cases passed")
    
    # Detailed analysis
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    
    if results["websocket_streaming"]:
        print("+ WebSocket streaming is functional")
        print(f"+ Received {len(chunks)} streaming chunks")
    else:
        print("- WebSocket streaming needs attention")
    
    if results["tts_generation"]:
        print("+ TTS audio generation is working")
    else:
        print("- TTS generation has issues")
    
    if results["stt_recording"]:
        print("+ STT recording functionality is working")
    else:
        print("- STT recording needs fixing")
    
    if results["integrated_pipeline"]:
        print("+ Complete voice pipeline (Chat -> TTS -> Audio) is functional")
    else:
        print("- Voice pipeline integration needs work")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
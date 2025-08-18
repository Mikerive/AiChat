"""
WebSocket endpoints for real-time communication
"""

import json
import logging
import sys
import asyncio
import time
from typing import Dict, Any, List
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from event_system import get_event_system, EventType, EventSeverity
from database import db_ops
from backend.chat_app.services.service_manager import get_whisper_service, get_chat_service

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_info: Dict[str, Any] = None):
        """Accept a WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_info[websocket] = client_info or {}
        logger.info(f"WebSocket connection established. Total connections: {len(self.active_connections)}")
        
        # Send welcome message
        welcome_message = {
            "type": "connection",
            "event": "connected",
            "message": "WebSocket connection established",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        await websocket.send_text(json.dumps(welcome_message))
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.client_info:
            del self.client_info[websocket]
        logger.info(f"WebSocket connection closed. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific client"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients, respecting per-client subscriptions.

        The frontend may send a subscription list when connecting (subscribe message). If a client
        has a "subscriptions" list in its client_info, only events matching those subscription keys
        will be delivered to that client. If no subscriptions are set for a client, it will receive
        all events.
        """
        disconnected = []

        # Try to parse event type from the message so we can respect subscriptions.
        event_type = ""
        try:
            payload = json.loads(message) if isinstance(message, str) else message
            if isinstance(payload, dict):
                # common keys: event_type (from Event.to_dict), type (legacy), event (legacy)
                event_type = payload.get("event_type") or payload.get("type") or payload.get("event") or ""
        except Exception:
            payload = None

        for connection in self.active_connections:
            try:
                client_info = self.client_info.get(connection, {}) or {}
                subs = client_info.get("subscriptions")
                # If client has explicit subscriptions, only deliver if the event_type matches one of them.
                if subs and isinstance(subs, list) and event_type:
                    if event_type not in subs:
                        continue

                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def subscribe_to_events(self, websocket: WebSocket, event_types: List[str]):
        """Subscribe client to specific event types"""
        if websocket in self.client_info:
            self.client_info[websocket]["subscriptions"] = event_types
            logger.info(f"Client subscribed to events: {event_types}")
    
    async def get_client_info(self, websocket: WebSocket) -> Dict[str, Any]:
        """Get client information"""
        return self.client_info.get(websocket, {})


# Global connection manager
connection_manager = ConnectionManager()

# Streaming session state for live (incremental) transcription
# session: {
#   "buffer": bytearray(),
#   "task": asyncio.Task,
#   "last_text": str,
#   "last_update": float
# }
STREAM_SESSIONS: Dict[str, Dict[str, Any]] = {}
# configuration
STREAM_POLL_INTERVAL = 0.8  # seconds between incremental transcribe attempts
STREAM_INACTIVITY_TIMEOUT = 5.0  # seconds of no incoming chunks to finalize session


@router.get("/ws-test")
async def websocket_test():
    """Simple WebSocket test page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Audio Stream Test</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 16px; }
            #devices { margin-bottom: 8px; }
            #meter { width: 300px; height: 16px; background: #eee; border-radius: 4px; overflow: hidden; }
            #meter-fill { height: 100%; width: 0%; background: #4caf50; transition: width 0.1s; }
            #transcript { white-space: pre-wrap; border: 1px solid #ddd; padding: 8px; min-height: 60px; }
            button { margin-right: 8px; }
            .indicator { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align:middle; }
            .indicator.on { background: #4caf50; }
            .indicator.off { background: #bbb; }
        </style>
    </head>
    <body>
        <h1>WebSocket Audio Stream & Whisper Test</h1>
        <div id="controls">
            <div id="devices">
                <label>Input:
                    <select id="inputDevices"></select>
                </label>
                <label>Output:
                    <select id="outputDevices"></select>
                </label>
            </div>
            <div>
                <button id="startBtn">Start Capture</button>
                <button id="stopBtn" disabled>Stop Capture</button>
                <span class="indicator off" id="recIndicator"></span><span id="recLabel">Not sending</span>
            </div>
            <div style="margin-top:8px;">
                <div id="meter"><div id="meter-fill"></div></div>
            </div>
        </div>
        <h3>Live Transcription</h3>
        <div id="transcript">No transcription yet</div>
        <h3>Event Log</h3>
        <div id="log"></div>
        <script>
            const logEl = document.getElementById('log');
            const transcriptEl = document.getElementById('transcript');
            const recIndicator = document.getElementById('recIndicator');
            const recLabel = document.getElementById('recLabel');
            const meterFill = document.getElementById('meter-fill');
            let ws;
            let mediaStream = null;
            let audioContext = null;
            let processor = null;
            let sourceNode = null;
            let inputDeviceId = null;
            let outputDeviceId = null;
            let sending = false;
            let sequence = 0;
            const CHUNK_MS = 500; // send every 500ms

            function log(msg) {
                const t = new Date().toISOString();
                logEl.innerHTML += `<div>[${t}] ${msg}</div>`;
                logEl.scrollTop = logEl.scrollHeight;
            }

            async function initWebSocket() {
                ws = new WebSocket("ws://localhost:8765/api/ws");
                ws.onopen = () => {
                    log('WebSocket connected');
                    // subscribe for events
                    ws.send(JSON.stringify({type: 'subscribe', events: ['audio_transcribed', 'audio_captured', 'chat.response']}));
                };
                ws.onmessage = (ev) => {
                    try {
                        const data = JSON.parse(ev.data);
                        // handle transcription updates & audio acknowledgements
                        if (data.type === 'transcription' || data.type === 'transcription_update' || data.type === 'transcription_partial') {
                            transcriptEl.textContent = data.text || data.partial || data.message || '';
                        } else if (data.type === 'audio_received' || data.type === 'transcription_in_progress') {
                            log('Server: ' + JSON.stringify(data));
                        } else if (data.type === 'chat_complete') {
                            log('Chat response: ' + (data.character_response || ''));
                        } else {
                            // generic event log
                            log('Server message: ' + JSON.stringify(data));
                        }
                    } catch (e) {
                        log('Received non-JSON message');
                    }
                };
                ws.onclose = () => log('WebSocket closed');
                ws.onerror = (e) => log('WebSocket error: ' + e);
            }

            async function enumerateDevices() {
                const devices = await navigator.mediaDevices.enumerateDevices();
                const inputs = devices.filter(d => d.kind === 'audioinput');
                const outputs = devices.filter(d => d.kind === 'audiooutput');
                const inputSelect = document.getElementById('inputDevices');
                const outputSelect = document.getElementById('outputDevices');
                inputSelect.innerHTML = '';
                outputSelect.innerHTML = '';
                inputs.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.deviceId;
                    opt.text = d.label || ('Input ' + (inputSelect.length+1));
                    inputSelect.appendChild(opt);
                });
                outputs.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.deviceId;
                    opt.text = d.label || ('Output ' + (outputSelect.length+1));
                    outputSelect.appendChild(opt);
                });
                inputSelect.onchange = () => { inputDeviceId = inputSelect.value; };
                outputSelect.onchange = () => { outputDeviceId = outputSelect.value; setOutputDevice(outputDeviceId); };
                if (inputSelect.options.length) inputDeviceId = inputSelect.options[0].value;
                if (outputSelect.options.length) outputDeviceId = outputSelect.options[0].value;
            }

            function setOutputDevice(deviceId) {
                // set audio output if supported
                const audioEls = document.getElementsByTagName('audio');
                for (let a of audioEls) {
                    if (typeof a.setSinkId === 'function') {
                        a.setSinkId(deviceId).then(() => log('Output device set')).catch(e => log('Error setting output device: ' + e));
                    }
                }
            }

            function encodeWAV(samples, sampleRate) {
                const buffer = new ArrayBuffer(44 + samples.length * 2);
                const view = new DataView(buffer);

                function writeString(view, offset, string) {
                    for (let i = 0; i < string.length; i++) {
                        view.setUint8(offset + i, string.charCodeAt(i));
                    }
                }

                let offset = 0;
                writeString(view, offset, 'RIFF'); offset += 4;
                view.setUint32(offset, 36 + samples.length * 2, true); offset += 4;
                writeString(view, offset, 'WAVE'); offset += 4;
                writeString(view, offset, 'fmt '); offset += 4;
                view.setUint32(offset, 16, true); offset += 4;
                view.setUint16(offset, 1, true); offset += 2;
                view.setUint16(offset, 1, true); offset += 2;
                view.setUint32(offset, sampleRate, true); offset += 4;
                view.setUint32(offset, sampleRate * 2, true); offset += 4;
                view.setUint16(offset, 2, true); offset += 2;
                view.setUint16(offset, 16, true); offset += 2;
                writeString(view, offset, 'data'); offset += 4;
                view.setUint32(offset, samples.length * 2, true); offset += 4;

                // PCM samples
                const volume = 1;
                let index = 44;
                for (let i = 0; i < samples.length; i++, index += 2) {
                    let s = Math.max(-1, Math.min(1, samples[i] * volume));
                    view.setInt16(index, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
                }

                return new Blob([view], { type: 'audio/wav' });
            }

            async function startCapture() {
                if (!inputDeviceId) {
                    await enumerateDevices();
                }
                mediaStream = await navigator.mediaDevices.getUserMedia({ audio: { deviceId: inputDeviceId ? { exact: inputDeviceId } : undefined } });
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                sourceNode = audioContext.createMediaStreamSource(mediaStream);
                const bufferSize = 4096;
                processor = audioContext.createScriptProcessor(bufferSize, 1, 1);
                let pcmBuffer = [];
                let pcmBufferLength = 0;
                const sampleRate = audioContext.sampleRate;

                sourceNode.connect(processor);
                processor.connect(audioContext.destination);

                const analyser = audioContext.createAnalyser();
                sourceNode.connect(analyser);
                analyser.fftSize = 1024;
                const dataArray = new Uint8Array(analyser.frequencyBinCount);

                processor.onaudioprocess = function(e) {
                    const inputData = e.inputBuffer.getChannelData(0);
                    // copy into PCM buffer
                    const chunk = new Float32Array(inputData.length);
                    chunk.set(inputData);
                    pcmBuffer.push(chunk);
                    pcmBufferLength += chunk.length;

                    // compute RMS for level meter
                    let sum = 0;
                    for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
                    const rms = Math.sqrt(sum / inputData.length);
                    const level = Math.min(1, rms * 10);
                    meterFill.style.width = Math.round(level * 100) + '%';
                };

                // send chunks periodically
                sending = true;
                recIndicator.classList.remove('off'); recIndicator.classList.add('on'); recLabel.textContent = 'Sending';
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;

                async function sendLoop() {
                    while (sending) {
                        if (pcmBufferLength > 0) {
                            // merge buffers
                            let merged = new Float32Array(pcmBufferLength);
                            let offset = 0;
                            for (let b of pcmBuffer) {
                                merged.set(b, offset);
                                offset += b.length;
                            }
                            pcmBuffer = [];
                            pcmBufferLength = 0;

                            // encode to WAV blob
                            const wavBlob = encodeWAV(merged, sampleRate);
                            const arrayBuffer = await wavBlob.arrayBuffer();
                            const bytes = new Uint8Array(arrayBuffer);
                            const base64Chunk = btoa(String.fromCharCode.apply(null, bytes));
                            const msg = {
                                type: 'audio_stream',
                                stream_id: 'local-' + (new Date().getTime()),
                                audio_data: base64Chunk
                            };
                            if (ws && ws.readyState === WebSocket.OPEN) {
                                ws.send(JSON.stringify(msg));
                                log('Sent audio chunk seq=' + (++sequence) + ' size=' + bytes.length);
                            }
                        }
                        await new Promise(r => setTimeout(r, CHUNK_MS));
                    }
                }

                sendLoop().catch(e => log('Send loop error: ' + e));
                log('Capture started');
            }

            function stopCapture() {
                sending = false;
                if (processor) {
                    processor.disconnect();
                    processor = null;
                }
                if (sourceNode) {
                    sourceNode.disconnect();
                    sourceNode = null;
                }
                if (audioContext) {
                    audioContext.close();
                    audioContext = null;
                }
                if (mediaStream) {
                    mediaStream.getTracks().forEach(t => t.stop());
                    mediaStream = null;
                }
                recIndicator.classList.remove('on'); recIndicator.classList.add('off'); recLabel.textContent = 'Not sending';
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                log('Capture stopped');
            }

            document.getElementById('startBtn').addEventListener('click', async () => {
                try {
                    if (!ws || ws.readyState !== WebSocket.OPEN) await initWebSocket();
                    await enumerateDevices();
                    await startCapture();
                } catch (e) {
                    log('Error starting capture: ' + e);
                }
            });
            document.getElementById('stopBtn').addEventListener('click', () => stopCapture());

            // initialize device list on load
            navigator.mediaDevices.getUserMedia({ audio: true }).then(() => {
                enumerateDevices().catch(e => log('Device enumeration error: ' + e));
            }).catch(e => log('Permission denied or no microphone: ' + e));
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint"""
    try:
        # Accept connection
        await connection_manager.connect(websocket)
        
        # Add to event system for broadcasting
        event_system = get_event_system()
        await event_system.add_websocket_connection(websocket)
        
        try:
            while True:
                # Wait for messages
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    await handle_websocket_message(websocket, message)
                    
                except json.JSONDecodeError:
                    error_message = {
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": "2024-01-01T00:00:00Z"
                    }
                    await websocket.send_text(json.dumps(error_message))
                    
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    error_message = {
                        "type": "error",
                        "message": f"Error processing message: {str(e)}",
                        "timestamp": "2024-01-01T00:00:00Z"
                    }
                    await websocket.send_text(json.dumps(error_message))
                    
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected by client")
            
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            
        finally:
            # Clean up
            connection_manager.disconnect(websocket)
            await event_system.remove_websocket_connection(websocket)
            
    except Exception as e:
        logger.error(f"WebSocket endpoint error: {e}")


async def handle_websocket_message(websocket: WebSocket, message: Dict[str, Any]):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "subscribe":
        # Subscribe to events
        event_types = message.get("events", [])
        await connection_manager.subscribe_to_events(websocket, event_types)
        
        response = {
            "type": "subscription",
            "event": "subscribed",
            "events": event_types,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        await websocket.send_text(json.dumps(response))
        
    elif message_type == "audio_stream":
        # Handle audio streaming data from frontend using server-side silence detection.
        audio_data = message.get("audio_data")
        stream_id = message.get("stream_id")
        
        if audio_data and stream_id:
            import base64
            # Decode base64 audio data (client sends WAV bytes)
            audio_bytes = base64.b64decode(audio_data)
            
            # Emit audio reception event (non-blocking ack)
            event_system = get_event_system()
            await event_system.emit(
                EventType.AUDIO_CAPTURED,
                "Audio stream chunk received from frontend",
                {
                    "stream_id": stream_id,
                    "audio_size": len(audio_bytes),
                    "source": "websocket_stream"
                }
            )
            
            # Acknowledge receipt to client so UI can show audio-received indicator
            try:
                await websocket.send_text(json.dumps({
                    "type": "audio_received",
                    "event": "chunk_received",
                    "stream_id": stream_id,
                    "audio_size": len(audio_bytes),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }))
            except Exception:
                pass

            # Feed audio to server-side silence/VAD based session buffer.
            try:
                from backend.chat_app.services.streaming_stt_service import feed_audio
                # feed_audio returns a temp WAV path when it decides the utterance is finalized by silence
                finalized_path = await asyncio.get_event_loop().run_in_executor(None, feed_audio, stream_id, audio_bytes)
            except Exception as e:
                logger.error(f"Error feeding audio to STT session for stream {stream_id}: {e}")
                finalized_path = None

            # If an utterance was finalized (silence detected), transcribe and send final result
            if finalized_path:
                try:
                    whisper_service = get_whisper_service()
                    transcription_result = await whisper_service.transcribe_audio(finalized_path)

                    # Emit transcription complete event (persistent)
                    await event_system.emit(
                        EventType.AUDIO_TRANSCRIBED,
                        "Speech-to-text transcription completed",
                        {
                            "stream_id": stream_id,
                            "text": transcription_result.get("text", ""),
                            "language": transcription_result.get("language", ""),
                            "confidence": transcription_result.get("confidence", 0.0)
                        }
                    )

                    # Send final transcription to frontend
                    transcription_response = {
                        "type": "transcription_final",
                        "event": "transcription_complete",
                        "stream_id": stream_id,
                        "text": transcription_result.get("text", ""),
                        "language": transcription_result.get("language"),
                        "confidence": transcription_result.get("confidence", 0.0),
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }
                    try:
                        await websocket.send_text(json.dumps(transcription_response))
                    except Exception:
                        pass

                    # Optionally pass final text to ChatService for LLM processing (preserve existing behavior)
                    if transcription_result.get("text"):
                        try:
                            chat_service = get_chat_service()
                            current_character = await chat_service.get_current_character()
                            if current_character:
                                chat_response = await chat_service.process_message(
                                    transcription_result["text"],
                                    current_character["id"],
                                    current_character["name"]
                                )

                                # Emit response generated event
                                await event_system.emit(
                                    EventType.CHAT_RESPONSE,
                                    "LLM response generated",
                                    {
                                        "stream_id": stream_id,
                                        "user_input": transcription_result["text"],
                                        "character_response": chat_response.response,
                                        "emotion": chat_response.emotion,
                                        "model_used": chat_response.model_used
                                    }
                                )

                                # Generate TTS and emit audio generated event if needed
                                tts_audio_path = await chat_service.generate_tts(
                                    chat_response.response,
                                    current_character["id"],
                                    current_character["name"]
                                )

                                await event_system.emit(
                                    EventType.AUDIO_GENERATED,
                                    "TTS audio generation completed",
                                    {
                                        "stream_id": stream_id,
                                        "audio_file": str(tts_audio_path) if tts_audio_path else None,
                                        "text": chat_response.response,
                                        "character": current_character["name"]
                                    }
                                )

                                complete_response = {
                                    "type": "chat_complete",
                                    "event": "response_ready",
                                    "stream_id": stream_id,
                                    "user_input": transcription_result["text"],
                                    "character_response": chat_response.response,
                                    "emotion": chat_response.emotion,
                                    "audio_file": str(tts_audio_path) if tts_audio_path else None,
                                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                                }
                                try:
                                    await websocket.send_text(json.dumps(complete_response))
                                except Exception:
                                    pass
                        except Exception as e:
                            logger.error(f"Error during chat processing for stream {stream_id}: {e}")

                finally:
                    # Clean up finalized temporary file
                    try:
                        import os
                        os.unlink(finalized_path)
                    except Exception:
                        pass
        
    elif message_type == "chat":
        # Handle chat message
        text = message.get("text")
        character = message.get("character", "hatsune_miku")
        
        if text:
            # Process chat message (this would normally call the chat service)
            response = {
                "type": "chat",
                "event": "message_sent",
                "text": text,
                "character": character,
                "timestamp": "2024-01-01T00:00:00Z"
            }
            await websocket.send_text(json.dumps(response))
            
            # Emit chat event to system
            event_system = get_event_system()
            await event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Chat message from {character}",
                {"text": text, "character": character}
            )
            
    elif message_type == "ping":
        # Handle ping/pong for connection health
        response = {
            "type": "pong",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        await websocket.send_text(json.dumps(response))
        
    elif message_type == "get_status":
        # Handle status request
        try:
            # Get system status
            from backend.api.routes.system import get_system_status
            status = await get_system_status()
            
            response = {
                "type": "status",
                "event": "status_update",
                "data": status,
                "timestamp": "2024-01-01T00:00:00Z"
            }
            await websocket.send_text(json.dumps(response))
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            error_response = {
                "type": "error",
                "message": f"Error getting status: {str(e)}",
                "timestamp": "2024-01-01T00:00:00Z"
            }
            await websocket.send_text(json.dumps(error_response))
            
    else:
        # Unknown message type
        error_response = {
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        await websocket.send_text(json.dumps(error_response))


# Event subscription handler for the event system
async def handle_event_broadcast(event):
    """Handle broadcasting events to WebSocket clients"""
    try:
        message = event.to_json()
        
        # Broadcast to all connected clients
        await connection_manager.broadcast(message)
        
    except Exception as e:
        logger.error(f"Error broadcasting event: {e}")


async def periodic_stream_transcribe(stream_id: str, websocket: WebSocket):
    """Background task: periodically transcribe accumulated audio buffer and send partial updates"""
    try:
        import tempfile
        import os

        whisper_service = get_whisper_service()
        session = STREAM_SESSIONS.get(stream_id)
        if session is None:
            return

        while True:
            await asyncio.sleep(STREAM_POLL_INTERVAL)

            session = STREAM_SESSIONS.get(stream_id)
            if session is None:
                break

            # If no new data since last poll and inactivity timeout exceeded, finalize and exit
            now = time.time()
            if (now - session["last_update"]) > STREAM_INACTIVITY_TIMEOUT:
                # finalize
                try:
                    # write buffer to temp file and transcribe final
                    if session["buffer"]:
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                            temp_file.write(bytes(session["buffer"]))
                            temp_path = temp_file.name
                        try:
                            final_result = await whisper_service.transcribe_audio(temp_path)
                            final_text = final_result.get("text", "")
                            # send final transcription
                            try:
                                await websocket.send_text(json.dumps({
                                    "type": "transcription_final",
                                    "stream_id": stream_id,
                                    "text": final_text,
                                    "language": final_result.get("language"),
                                    "confidence": final_result.get("confidence", 0.0),
                                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                                }))
                            except Exception:
                                pass
                        finally:
                            try:
                                os.unlink(temp_path)
                            except Exception:
                                pass
                except Exception as e:
                    logger.error(f"Error during final transcription for stream {stream_id}: {e}")

                # cleanup session
                STREAM_SESSIONS.pop(stream_id, None)
                break

            # If buffer has content, produce an incremental transcription and send partial if changed
            if session["buffer"]:
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                        temp_file.write(bytes(session["buffer"]))
                        temp_path = temp_file.name
                    try:
                        result = await whisper_service.transcribe_audio(temp_path)
                        text = result.get("text", "")
                        last = session.get("last_text", "")
                        if text and text != last:
                            session["last_text"] = text
                            try:
                                await websocket.send_text(json.dumps({
                                    "type": "transcription_partial",
                                    "stream_id": stream_id,
                                    "partial": text,
                                    "language": result.get("language"),
                                    "confidence": result.get("confidence", 0.0),
                                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                                }))
                            except Exception:
                                pass
                    finally:
                        try:
                            os.unlink(temp_path)
                        except Exception:
                            pass
                except Exception as e:
                    logger.error(f"Error transcribing buffer for stream {stream_id}: {e}")
                    # continue polling despite errors
    except Exception as e:
        logger.error(f"Unexpected error in periodic_stream_transcribe for {stream_id}: {e}")

async def process_audio_stream_chunk(websocket: WebSocket, audio_data: str, stream_id: str):
    # Backwards-compatible chunk processor (unused by incremental flow)
    try:
        import base64
        import tempfile
        import os

        # Decode base64 audio data
        audio_bytes = base64.b64decode(audio_data)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        try:
            # Speech-to-Text Pipeline: Whisper STT Service
            whisper_service = get_whisper_service()
            transcription_result = await whisper_service.transcribe_audio(temp_path)

            # Emit transcription complete event
            event_system = get_event_system()
            await event_system.emit(
                EventType.AUDIO_TRANSCRIBED,
                "Speech-to-text transcription completed",
                {
                    "stream_id": stream_id,
                    "text": transcription_result.get("text", ""),
                    "language": transcription_result.get("language", ""),
                    "confidence": transcription_result.get("confidence", 0.0)
                }
            )

            # Send transcription result to frontend
            transcription_response = {
                "type": "transcription",
                "event": "transcription_complete",
                "stream_id": stream_id,
                "text": transcription_result.get("text", ""),
                "language": transcription_result.get("language", ""),
                "confidence": transcription_result.get("confidence", 0.0),
                "timestamp": "2024-01-01T00:00:00Z"
            }
            await websocket.send_text(json.dumps(transcription_response))

            # Text sent to Chat Service for LLM Processing
            if transcription_result.get("text"):
                chat_service = get_chat_service()
                current_character = await chat_service.get_current_character()

                if current_character:
                    # LLM Processing: OpenRouter Service
                    chat_response = await chat_service.process_message(
                        transcription_result["text"],
                        current_character["id"],
                        current_character["name"]
                    )

                    # Emit response generated event
                    await event_system.emit(
                        EventType.CHAT_RESPONSE,
                        "LLM response generated",
                        {
                            "stream_id": stream_id,
                            "user_input": transcription_result["text"],
                            "character_response": chat_response.response,
                            "emotion": chat_response.emotion,
                            "model_used": chat_response.model_used
                        }
                    )

                    # Text-to-Speech Pipeline: Piper TTS Service
                    tts_audio_path = await chat_service.generate_tts(
                        chat_response.response,
                        current_character["id"],
                        current_character["name"]
                    )

                    # Audio Generation Event
                    await event_system.emit(
                        EventType.AUDIO_GENERATED,
                        "TTS audio generation completed",
                        {
                            "stream_id": stream_id,
                            "audio_file": str(tts_audio_path) if tts_audio_path else None,
                            "text": chat_response.response,
                            "character": current_character["name"]
                        }
                    )

                    # Send complete response to frontend
                    complete_response = {
                        "type": "chat_complete",
                        "event": "response_ready",
                        "stream_id": stream_id,
                        "user_input": transcription_result["text"],
                        "character_response": chat_response.response,
                        "emotion": chat_response.emotion,
                        "audio_file": str(tts_audio_path) if tts_audio_path else None,
                        "timestamp": "2024-01-01T00:00:00Z"
                    }
                    await websocket.send_text(json.dumps(complete_response))

        finally:
            # Clean up temporary file
            os.unlink(temp_path)

    except Exception as e:
        logger.error(f"Error processing audio stream chunk: {e}")
        error_response = {
            "type": "error",
            "event": "audio_processing_error",
            "stream_id": stream_id,
            "message": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }
        await websocket.send_text(json.dumps(error_response))


# Subscribe to all events when the module is loaded (async-safe)
event_system = get_event_system()
import asyncio
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(event_system.subscribe_to_all(handle_event_broadcast))
    else:
        loop.run_until_complete(event_system.subscribe_to_all(handle_event_broadcast))
except Exception:
    # If event system fails, continue without it
    pass
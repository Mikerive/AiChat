# whisper.cpp Streaming STT Integration Plan

Purpose: Provide a detailed integration plan to run whisper.cpp locally for low-latency, on-prem streaming STT and connect it to the existing WebSocket audio pipeline.

Overview

- Use a local whisper.cpp (ggml) binary or wrapper to perform incremental transcription.
- Transcode browser audio (WebM/Opus) to 16-bit PCM mono at a target sample rate (16k or 32k) using FFmpeg.
- Stream PCM frames to whisper.cpp via stdin or a local TCP/UNIX socket, receive partial and final text back, and forward to frontend through existing WS endpoint.

Affected repo files (examples)

- WebSocket handler: [`backend/chat_app/routes/websocket.py:140`](backend/chat_app/routes/websocket.py:140)
- New adapter/service: [`backend/chat_app/services/streaming_stt_service.py:1`](backend/chat_app/services/streaming_stt_service.py:1)
- Existing whisper batch service (fallback): [`backend/chat_app/services/whisper_service.py:65`](backend/chat_app/services/whisper_service.py:65)

Data flow

1. Frontend records short chunks (200–500 ms) with MediaRecorder (Opus/WebM) and sends base64 blobs to WS.
2. WS handler forwards blobs to StreamingSTTService for the session identified by stream_id.
3. StreamingSTTService decodes blob, pipes raw audio (PCM s16le) to ffmpeg if needed, and streams PCM to whisper.cpp.
4. whisper.cpp emits partial and final transcripts, adapter parses and emits events to EventSystem and forwards messages to the WS client.

Transcoding details

- Recommended ffmpeg pipeline (blob -> PCM WAV):
  ffmpeg -i pipe:0 -ar 16000 -ac 1 -f wav -sample_fmt s16 pipe:1
- For file-based conversion:
  ffmpeg -hide_banner -loglevel error -i input.webm -ar 16000 -ac 1 -f wav -sample_fmt s16 output.wav
- Use a persistent ffmpeg subprocess per session to avoid per-chunk startup overhead.

whisper.cpp modes

- Subprocess stdin streaming: spawn whisper.cpp and write PCM to stdin if the binary supports streaming input and outputs partial results.
- TCP/HTTP wrapper: run or ship a small server that exposes a socket API; adapter connects and streams audio over socket.
- File-based segmentation: write small WAV segments and call whisper.cpp on each segment; simpler but less efficient and less accurate for partials.

Recommended approach

- Start with a per-session ffmpeg subprocess plus a whisper.cpp wrapper process that accepts PCM over stdin and emits JSON line messages with partial/final text.
- If no wrapper exists, implement a minimal C++ or Python layer that invokes whisper.cpp inference APIs and writes partial results to stdout or socket.

Adapter design

- Class: WhisperCppAdapter
  - start_session(stream_id, model, options) -> session object
  - send_audio(session, bytes) -> immediate ack
  - end_session(session) -> await final transcription
  - abort_session(session) -> kill subprocesses and cleanup
- Session internals:
  - ffmpeg_proc: subprocess for decoding browser blobs to PCM
  - whisper_proc / wrapper_conn: subprocess or socket connected to whisper.cpp
  - buffers, seq counters, timestamp tracking

Concurrency & resource limits

- Use an asyncio.Semaphore for MAX_CONCURRENT_STREAMS (configurable; default: 2–4).
- Monitor CPU and memory; choose GGML model sizes based on available CPU (tiny/base for real-time on single CPU core).
- Provide admin endpoint to query current sessions and health.

Message protocol (WS)

- Client -> Server:
  { "type": "audio_stream", "stream_id": "...", "seq": n, "audio_data": "<base64>" }
  { "type": "end_stream", "stream_id": "..." }
- Server -> Client:
  { "type": "audio_received", "stream_id": "...", "seq": n }
  { "type": "transcription_partial", "stream_id": "...", "seq": n, "partial": "..." }
  { "type": "transcription_final", "stream_id": "...", "seq": n, "text": "..." }

Testing strategy

- Unit tests: mock WhisperCppAdapter to emit partial/final messages; assert WS handler forwards them and EventSystem events are emitted.
- Integration test: create a TestClient WebSocket that sends pre-recorded small blob(s) and asserts receipt of audio_received and transcription_final messages.
- Performance testing: simulate multiple concurrent clients to measure latency and CPU.

Deployment & installation

- Build or download whisper.cpp binary and place it in a configured path (e.g., WHISPER_CPP_BIN).
- Download desired ggml model files and place in MODELS_DIR.
- Install ffmpeg on the host and ensure it's on PATH.
- Add env vars to .env or configuration:
  - WHISPER_CPP_BIN=/opt/whisper.cpp/main
  - WHISPER_MODELS_DIR=/opt/whisper_models
  - STREAMING_STT_MAX_CONCURRENT=2

Security & privacy

- Keep everything local; do not upload audio to third-party services.
- Validate and limit session durations and file sizes to avoid resource exhaustion.

Rollout plan (phased)

- Phase 1 (prototype): implement adapter that runs per-session ffmpeg + whisper.cpp command, parse outputs, and forward transcripts. Add integration test that uses a short WAV fixture. (~2–3 days)
- Phase 2 (robustness): add semaphores, session cleanup, health endpoints, and model selection. (~1–2 days)
- Phase 3 (performance): tune ffmpeg pipeline, experiment with reuse of processes, and add monitoring/metrics. (~1–2 days)

Caveats & limitations

- whisper.cpp model size affects latency and CPU; test with tiny/base models first.
- Partial accuracy may be lower on very small chunks; consider chunk overlap or a small buffering window (300–500 ms).
- Windows vs Unix differences: named pipes and signal handling differ; prefer stdin/stdout or TCP sockets for portability.

Minimal implementation checklist

- [ ] Add [`backend/chat_app/services/streaming_stt_service.py:1`](backend/chat_app/services/streaming_stt_service.py:1) with adapter scaffold.
- [ ] Update WS handler [`backend/chat_app/routes/websocket.py:140`](backend/chat_app/routes/websocket.py:140) to route audio_stream messages to adapter.
- [ ] Add ffmpeg helper utility to spawn persistent per-session ffmpeg.
- [ ] Add integration tests in `backend/tts_finetune_app/tests/` using TestClient WebSocket.
- [ ] Document install steps in README and add env vars to `.env.example`.

Example ffmpeg + whisper.cpp pipeline (concept)

- Start whisper wrapper (example):
  WHISPER_CPP_BIN=./main ./main -m models/ggml-base.bin --server-mode
- Server receives PCM on socket, wrapper returns JSON lines:
  {"type":"partial","text":"this is a par"}
  {"type":"partial","text":"this is a partial"}
  {"type":"final","text":"this is a partial transcription"}

Final notes

- I can implement the Phase 1 prototype next: scaffold adapter, wire WS handler, and add an integration test. Choose whether you want the wrapper binary (I can include a small wrapper suggestion) or to rely on an existing whisper.cpp build that supports streaming.
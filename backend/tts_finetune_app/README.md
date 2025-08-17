# TTS Finetune App — Pipeline & Implementation Notes

This folder is the renamed implementation area for the voice training pipeline. It holds the preprocessing and training utilities migrated from [`backend/voice_trainer/audio_processor.py`](backend/voice_trainer/audio_processor.py:1) and [`backend/voice_trainer/train_voice.py`](backend/voice_trainer/train_voice.py:1). Final code artifacts will live here under the `backend/tts_finetune_app/` namespace (examples below).

Overview
- Purpose: convert long mp3/mp4 inputs into training-ready speech clips, transcribe clips with Whisper, produce a CSV manifest (clip_filename | transcript), generate Piper-compatible manifests, and run Piper finetuning with epoch-level checkpointing.
- Durable design: each major stage writes checkpoints and atomic metadata so long-running jobs can resume safely.

Key files (source -> new location)
- Preprocessing and segmentation: [`backend/voice_trainer/audio_processor.py`](backend/voice_trainer/audio_processor.py:1) -> [`backend/tts_finetune_app/audio_processor.py`](backend/tts_finetune_app/audio_processor.py:1)
- Training orchestration: [`backend/voice_trainer/train_voice.py`](backend/voice_trainer/train_voice.py:1) -> [`backend/tts_finetune_app/train_voice.py`](backend/tts_finetune_app/train_voice.py:1)
- Streaming metadata CSV example: [`backend/voice_trainer/training_data/metadata.csv`](backend/voice_trainer/training_data/metadata.csv:1) -> [`backend/tts_finetune_app/training_data/metadata.csv`](backend/tts_finetune_app/training_data/metadata.csv:1)

Pipeline summary
1. Ingest
   - Accept mp3/mp4 uploads or directory of files.
   - Extract audio via ffmpeg to WAV at target sample rate (default 22050 Hz).
   - Persist original in `training_data/raw/` with checksum and job-sidecar JSON.

2. Source separation (Spleeter)
   - Run Spleeter (2-stem) to extract vocal stem.
   - Save vocal stem to `training_data/vocals/`.
   - Mark separation complete in job checkpoint JSON.

3. Recursive silence-based segmentation
   - Compute RMS envelope.
   - Start with an initial silence factor and split on silence midpoints.
   - If segments exceed MAX_AUDIO_LENGTH, lower factor and recurse.
   - Save segments atomically to `training_data/audio/`.

4. Per-clip preprocessing
   - Resample, normalize, optional denoise, trim micro-silence.
   - Enforce min/max clip lengths and merge very short neighbors.
   - Save final processed WAV.

5. Whisper transcription
   - Worker pool transcribes clips as they finish.
   - Append rows to `training_data/metadata.csv` with atomic write: clip_filename|transcript|duration|speaker|quality
   - Save per-clip JSON with confidence and language.

6. Piper manifest generation
   - Convert `metadata.csv` to Piper's dataset layout (ljspeech or dataset.jsonl + .pt spectrograms) using `piper_train.preprocess`.
   - Validate audio (wav, 16-bit, mono, sample rate 22050 or 16000 as chosen).

7. Training orchestration
   - Run `python -m piper_train --dataset-dir <dir> ...` with checkpoint epochs configured.
   - Save model checkpoints per epoch and maintain resume info in job JSON.

Durability and resume strategy
- Job JSON (checkpoints/<job_id>.json) records stage booleans and counters:
  - ingested, separated, segments_saved, transcribed_count, manifest_created, training: { epoch, last_checkpoint }
- Atomic write pattern:
  - Write to temp file, fsync if possible, then rename to final path.
  - CSV appends should use per-clip temporary row files merged periodically or use file locks for append.

Mermaid dataflow (renderable)
graph LR
  A[Ingest mp3/mp4 -> extract WAV] --> B[Spleeter: vocals + accompaniment]
  B --> C[Compute RMS energy envelope]
  C --> D[Recursive silence-based splitter]
  D --> E[Per-clip preprocessing (resample, normalize, trim)]
  E --> F[Save clip WAV (atomic)]
  F --> G[Whisper transcription worker]
  G --> H[Append to CSV: clip_name | transcript]
  H --> I[Piper manifest generator]
  I --> J[Training orchestrator (epochs + checkpointing)]
  J --> K[Model checkpoints & logs]

Next actions performed by the project
- Copy existing preprocessing/training code here and continue development.
- Implement CLI wrappers and API endpoints that reference this new folder.
- Provide tests for splitting, transcription, CSV generation, and training flows.

Notes for maintainers
- Search the codebase for references to `backend/voice_trainer` and update imports to `backend/tts_finetune_app` if you intend to fully replace the old folder. For backward compatibility, both folders can coexist until references are updated.
- The original files used for migration:
  - [`backend/voice_trainer/audio_processor.py`](backend/voice_trainer/audio_processor.py:1)
  - [`backend/voice_trainer/train_voice.py`](backend/voice_trainer/train_voice.py:1)
  - [`backend/voice_trainer/training_data/metadata.csv`](backend/voice_trainer/training_data/metadata.csv:1)

Usage example (development)
- Preprocess a single file:
  python backend/tts_finetune_app/train_voice.py preprocess --input /path/to/raw_dir --output backend/tts_finetune_app/training_data/wavs
- Prepare Piper dataset:
  python -m piper_train.preprocess --language en-us --input-dir backend/tts_finetune_app/training_data --output-dir backend/tts_finetune_app/piper_dataset --dataset-format ljspeech --single-speaker --sample-rate 22050

Stored artifacts (folder layout)
- backend/tts_finetune_app/
  - audio_processor.py
  - train_voice.py
  - training_data/
    - raw/
    - vocals/
    - audio/
    - metadata.csv

This README will be followed by copying the current implementations into this folder. After the files are copied I will update the todo list to mark migration steps complete.